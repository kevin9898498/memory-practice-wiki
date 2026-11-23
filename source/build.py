"""Compile the reviewed LLM Wiki, lesson and actual check results to offline HTML."""
import argparse
from copy import deepcopy
import json
from pathlib import Path
import re
from tempfile import TemporaryDirectory
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parent
SCOPE = [
    {"question": "這堂課給誰？", "decision": "給第一次聽到這兩種方法的大學生。學完能區分兩個概念、實作一題並排出自己的複習計畫。"},
    {"question": "先問 Wiki 哪些問題？", "decision": "怎麼安排間隔？提取練習是什麼？答對後還要再練嗎？答完如何核對？怎麼把兩種方法合在一起？"},
    {"question": "如何處理證據與示例？", "decision": "納入五篇原始實驗，每篇保留方法、結果、限制。簡報用主張 ID 查回 Wiki，跨日計畫標示為教學示例。"},
]


def read_json(name):
    return json.loads((ROOT / name).read_text(encoding="utf-8"))


def unique_index(records, name):
    result = {record["id"]: record for record in records}
    if len(result) != len(records):
        raise ValueError(f"{name}出現重複 ID")
    if any(not re.fullmatch(r"[A-Za-z][A-Za-z0-9-]*", key) for key in result):
        raise ValueError(f"{name}出現無法當作錨點的 ID")
    return result


def load_wiki():
    sources = read_json("sources.json")
    wiki = read_json("concepts.json")
    by_source = unique_index(sources, "來源")
    by_topic = unique_index(wiki["topics"], "概念頁")
    by_claim = unique_index([claim for topic in by_topic.values() for claim in topic["claims"]], "主張")
    unique_index(sources + list(by_topic.values()) + list(by_claim.values()), "Wiki 錨點")
    if len(sources) < 5 or len({source["doi"] for source in sources}) != len(sources):
        raise ValueError("需要至少五篇獨立、具有 DOI 的來源")
    for source in sources:
        url = urlparse(source["url"])
        if url.scheme != "https" or not url.netloc or not source["doi"].startswith("10."):
            raise ValueError(f"{source['id']} 缺原文連結或 DOI")
        archive_path = Path("raw") / f"{source['id']}.md"
        archive = ROOT.parent / archive_path
        if not archive.is_file() or source["doi"] not in archive.read_text(encoding="utf-8"):
            raise ValueError(f"{source['id']} 缺少含有相符 DOI 的原始資料卡")
        source["rawPath"] = archive_path.as_posix()
        for key in ("title", "authors", "journal", "method", "result", "limit"):
            if not source[key].strip():
                raise ValueError(f"{source['id']} 缺少 {key}")
    for topic in by_topic.values():
        if not set(topic["seeAlso"]).issubset(by_topic):
            raise ValueError(f"{topic['id']} 有無效的概念連結")
    for claim in by_claim.values():
        if not claim["sourceIds"] or not set(claim["sourceIds"]).issubset(by_source):
            raise ValueError(f"{claim['id']} 要先回查或補入 Wiki 來源")
        if not claim["context"].strip():
            raise ValueError(f"{claim['id']} 缺少適用範圍")
    wiki["sources"] = sources
    return wiki, by_claim


def resolve_lesson(draft, claims):
    deck = deepcopy(draft)
    unique_index(deck["slides"], "簡報頁")
    for slide in deck["slides"]:
        ids = slide.pop("cite", [])
        for block in slide["blocks"]:
            claim_id = block.pop("claim", None)
            if claim_id is not None:
                if claim_id not in claims:
                    raise ValueError(f"{slide['id']} 找不到 {claim_id}，需回查 Wiki")
                ids.append(claim_id)
                block["text"] = claims[claim_id]["text"]
        if not ids or not set(ids).issubset(claims):
            raise ValueError(f"{slide['id']} 缺有效 Wiki 引用")
        slide["refs"] = [{"id": key, "label": claims[key]["label"], "href": f"wiki.html#{key}"}
                         for key in dict.fromkeys(ids)]
        if "quiz" in slide:
            quiz = slide["quiz"]
            if not 0 <= quiz["answer"] < len(quiz["options"]) == len(quiz["explanations"]):
                raise ValueError(f"{slide['id']} 的作答選項和解說須一一對應")
    return deck


def check_scope(deck, claims):
    issues = []
    for number, slide in enumerate(deck["slides"], 1):
        copy = " ".join([slide["title"], slide.get("lead", ""), slide.get("note", "")] +
                        [block["text"] for block in slide["blocks"]] +
                        [event["description"] for event in slide.get("timeline", [])])
        if re.search(r"(?:每次|總是|一定|永遠)都?比重讀(?:有效|好)", copy):
            issues.append(f"第 {number} 頁的提取練習寫成普遍優於重讀，須回查 C04 與 S2 的測驗條件。")
        if slide["type"] == "timeline":
            example = any(claims[ref["id"]]["kind"] == "應用" for ref in slide["refs"])
            if not example or "教學示例" not in slide.get("note", "") or re.search(r"最佳|保證", copy):
                issues.append(f"第 {number} 頁的日程須標示教學示例，須回查 C08、S1 與 S5。")
    return issues


def render(template_name, marker, data, destination):
    template = (ROOT / template_name).read_text(encoding="utf-8")
    if template.count(marker) != 1:
        raise ValueError(f"{template_name} 缺少唯一的資料位置")
    payload = json.dumps(data, ensure_ascii=False).replace("<", "\\u003c")
    destination.write_text(template.replace(marker, payload), encoding="utf-8")


def run_probe(draft, claims):
    probe = deepcopy(draft)
    by_slide = unique_index(probe["slides"], "測試頁")
    by_slide["test-delay"]["lead"] = "提取練習每次都比重讀有效。"
    by_slide["one-week"]["note"] = "第 1、3、6 天是最佳複習時程。"
    test_deck = resolve_lesson(probe, claims)

    with TemporaryDirectory(dir=ROOT) as scratch:
        late_file = Path(scratch) / "probe.html"
        render("deck-template.html", "{{DECK_DATA}}", test_deck, late_file)
        late = check_scope(test_deck, claims)
        if len(late) != 2 or not late_file.is_file():
            raise ValueError("改版前測試未再現預期的兩個問題")
        early_file = Path(scratch) / "guarded.html"
        early = check_scope(test_deck, claims)
        if not early:
            render("deck-template.html", "{{DECK_DATA}}", test_deck, early_file)
        if early != late or early_file.exists():
            raise ValueError("提前檢查未阻止錯誤稿輸出")

    return [
        {"name":"測試 1｜改版前", "phase":"輸出後檢查", "status":"攔下 2 項", "errors":late,
         "detail":"刻意把兩個常見錯句放進測試稿。流程先在暫存區產生一份 HTML，檢查時才攔下。"},
        {"name":"測試 2｜改版後", "phase":"排版前檢查", "status":"攔下 2 項", "errors":early,
         "detail":"以相同測試稿重跑，兩個問題都在大綱階段被攔下。這次未產生該測試稿的 HTML。"},
    ]


def build(destination):
    wiki, claims = load_wiki()
    draft = read_json("lesson.json")
    runs = run_probe(draft, claims)
    deck = resolve_lesson(draft, claims)
    errors = check_scope(deck, claims)
    if errors:
        raise ValueError("\n".join(errors))

    mapping = [{"slide": i, "title": slide["title"].replace("\n", ""),
                "claims": [{"id": ref["id"], "href": ref["href"], "sources": claims[ref["id"]]["sourceIds"]}
                           for ref in slide["refs"]]} for i, slide in enumerate(deck["slides"], 1)]
    runs.append({"name":"正式稿", "phase":"審完大綱再排版", "status":"通過", "errors":[],
                 "detail":"第 3 頁使用 C04 的短文測驗情境，第 5 頁引用 C08 並標作教學示例。引用、題目結構和範圍規則均通過。"})
    if (ROOT / "browser-run.json").is_file():
        runs.extend(read_json("browser-run.json"))
    report = {
        "scope": SCOPE,
        "runs": runs,
        "stats": {"sources": len(wiki["sources"]), "topics": len(wiki["topics"]), "claims": len(claims),
                  "slides": len(deck["slides"]), "refs": sum(len(item["claims"]) for item in mapping)},
        "reflection": [
            {"question":"哪個節點最容易出錯？", "answer":"這次刻意測試的兩個問題，都發生在把研究改寫成教學大綱時。一個把特定測驗結果寫成通則，另一個把示例日期寫成最佳時程。一次回歸測試只能指出這次驗證的風險。"},
            {"question":"檢查往前移到了哪裡？", "answer":"從 HTML 初稿完成後，移到查回 Wiki 主張、組好簡報大綱之後。先核對材料、測驗延遲與示例標籤，再允許進入排版。"},
            {"question":"有修改 graph 嗎？", "answer":"有。增加大綱檢查到改寫的回邊。主張有依據但寫得過頭時，回到大綱修正該頁。查不到依據時，回到 Wiki 查詢，必要時補讀來源再整理。瀏覽器仍在輸出後檢查互動和連結。"},
        ],
        "mapping": mapping,
    }
    destination.mkdir(parents=True, exist_ok=True)
    render("wiki-template.html", "{{WIKI_DATA}}", wiki, destination / "wiki.html")
    render("deck-template.html", "{{DECK_DATA}}", deck, destination / "index.html")
    render("workflow-template.html", "{{REPORT_DATA}}", report, destination / "workflow.html")
    (ROOT / "run-results.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"stats": report["stats"], "runs": [{"name": r["name"], "status": r["status"]} for r in runs]}, ensure_ascii=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    build(parser.parse_args().output)
