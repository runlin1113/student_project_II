# 项目长期记忆 · project_II（大三上 项目实践2）

## 仓库与开源
- 本仓库内容仅 `week3/`（第三周项目实践：上云服务智能体·智能体推理模块的数据模拟文献调研）。
- 远程仓库：`runlin1113/student_project_II`（GitHub，公开）。
- 已连接的 GitHub MCP `push_files` **只能无损上传文本文件**，二进制（PNG/PPTX/图片/压缩包）经它会损坏。
- 含二进制时正确做法：本地 `git init` → `git add -A` → `git commit` → 用用户提供的 GitHub PAT 经 `git push` 推到 `main`；推送后用 `git remote set-url origin https://github.com/<owner>/<repo>.git` 把令牌从 remote URL 清除（不写入任何配置文件、不留凭据）。
- 校验无损：比对本地 `git rev-parse HEAD:<path>` 的 blob SHA 与 GitHub 上对应文件 blob SHA 是否一致。

## 用户偏好（本项目）
- README 要求「简述仓库里有什么就行」，不要冗长。
- 内容真实，不编造。
