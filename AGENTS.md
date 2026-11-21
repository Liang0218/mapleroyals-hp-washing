# 工作規則

- 每次修改程式碼、設定或測試後，完成前都必須執行相關測試。
- 修改 Python 核心或桌面版時，執行 `python -m pytest`。
- 修改網頁版時，在 `web` 目錄執行 `npm test`。
- 修改網頁版介面或操作流程時，另外在 `web` 目錄執行 `npm run test:e2e`（Playwright 操作測試，第一次需先執行 `npx playwright install chromium`）。
- 若修改同時影響 Python 與網頁版的共用計算邏輯，兩套測試都必須執行。
- 回覆時說明執行的測試結果；若測試無法執行，需說明原因。
