# 記憶練習簿

「間隔學習與提取練習」教學作業。先確定初學者的學習目標，再把五篇原始研究整理成四個概念、八則有依據的主張，以此製作七頁教學簡報。

## 瀏覽成果

- 一週複習示例與兩道互動題。[教學 HTML 簡報](https://kevin9898498.github.io/memory-practice-wiki/)
- 研究主張、情境與限制，支援搜尋。[Wiki 網頁](https://kevin9898498.github.io/memory-practice-wiki/wiki.html) · [Markdown 版 Wiki 索引](wiki/index.md)
- 生成前討論、迴圈、實跑紀錄、反思與逐頁引用對照。[製作流程與驗收](https://kevin9898498.github.io/memory-practice-wiki/workflow.html)

下載或複製此儲存庫後，用瀏覽器開啟根目錄的 `index.html`，即可離線使用網頁。原文連結需要網路。

## 專案結構

| 路徑 | 用途 |
| --- | --- |
| [`raw/`](raw/) | 五篇原始研究的來源紀錄、DOI 和原文連結。 |
| [`wiki/`](wiki/) | Wiki 索引、來源摘要、可互相連結的概念頁。 |
| [`schema/`](schema/) | 新增知識頁的格式範本。 |
| [`AGENTS.md`](AGENTS.md) | AI 協作規則、命名、存放位置和引用規則。 |
| [`source/`](source/) | 經查核的知識資料、教學大綱、HTML 範本和重建程式。 |

從儲存庫根目錄重建根目錄的三個 HTML，使用 Python 3，無須安裝套件。

```sh
python -X utf8 source/build.py .
```

## GitHub Pages 發佈

儲存庫須設為 **Public**。在 GitHub 打開 **Settings → Pages**，來源選 **Deploy from a branch**，分支選 `main`、路徑選 `/(root)` 並儲存。部署完成後，由 Pages 頁面取得網址。用未登入的瀏覽器開啟簡報、Wiki 與流程頁，再將可開啟的網址填入繳交表單。

繳交標題格式為 `〔學校〕 〔學號〕 〔系級〕 〔姓名〕 間隔學習與提取練習`。
