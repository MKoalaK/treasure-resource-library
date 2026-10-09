# Treasure Resource Library

[English](#english) · [中文介绍](#中文介绍)

## English

**Turn useful tools you discover into a searchable, updatable resource library with local visuals.**

Treasure Resource Library is an **Agent Skill for Codex and compatible agents**. Give it website names, URLs, or application names. The agent follows a consistent workflow to research each resource, summarize its capabilities and reputation, save visual material, and maintain a local Markdown table.

Use it to build a personal or shared collection of AI tools, design resources, productivity apps, and developer utilities.

### Features and benefits

| Feature | Why it helps |
| --- | --- |
| **Flexible input and batch collection** | Accepts one or more names, URLs, mobile apps, or desktop tools, reducing repetitive searching and manual copying. |
| **Separate product facts from user sentiment** | Draws on official information, independent reviews, and user feedback. Limited evidence is stated explicitly to support more informed comparisons. |
| **Consistent, concise entries** | Uses ten columns and exactly five tags per resource. Descriptions are limited to 200 characters; reviews are a single sentence of at most 150 characters—not words. |
| **Incremental maintenance** | Identifies existing products, appends new resources, updates entries when information materially changes, and leaves unchanged records untouched. |
| **Local media with screenshot fallback** | Prioritizes official images and videos. When downloads cannot be saved, it attempts to capture 1–3 screenshots of the homepage and key feature pages per resource. |
| **Visible verification gaps** | Retains discovered official URLs even when they cannot be verified, marking them as unverified in notes. Access errors and media failures remain visible for follow-up. |
| **Portable Markdown files** | Keeps the document and media under your control, with relative media paths for backup and migration to Obsidian or another Markdown table viewer. |
| **Respect for existing documents** | Appends to ordinary documents and preserves unrelated content when maintaining a library. File-version checks stop detected concurrent changes from being overwritten. |

### Output

A table without an automatically generated library heading. Its fields are:

**Name · Official URL · Description · Review · Type · Tags · Download options · Media · Updated at · Notes**

The current skill uses Chinese column labels and defaults to Chinese summaries. This bilingual README does not change that default.

Images and screenshots appear through local image references; videos use file links. Media is stored beside the document in `<document-stem>_素材/<resource-id>/`. If neither download nor screenshot capture succeeds, the agent falls back to verified source-page links and records the limitation.

### Installation and usage

Clone or extract this repository into `treasure-resource-library` under your Codex skills directory:

```text
~/.codex/skills/treasure-resource-library/SKILL.md
```

If `CODEX_HOME` is set, use its `skills/treasure-resource-library` directory instead. Keep the `agents/`, `references/`, and `scripts/` folders. For other compatible clients, follow their skill installation process and provide the required tools.

Example prompt:

```text
Use $treasure-resource-library to collect Notion, Obsidian, and https://reactbits.dev/.
```

The skill asks for a destination for each new task unless one was already supplied:

- **Folder:** creates or maintains `宝藏资源库.md` inside it.
- **Markdown file:** maintains an identified resource table or appends a new table to an ordinary document.
- **Previously collected resource:** compares the information and updates only material changes.

### Requirements and limits

- Requires a compatible agent with web search and page-reading tools; it is not a standalone background crawler.
- Requires **Python 3.10+**. Helper scripts use only the standard library.
- Screenshots require browser or app tools that can export image files. The skill does not automatically install target apps or bypass sign-in requirements.
- Verification describes the collection-time result, not permanent availability. Search and capture quality depend on the available tools and website access.
- Hidden maintenance markers remain in Markdown. Use Live Preview or Reading view in Obsidian for formatted tables, and move the media directory together with the document.

### Development and validation

Full workflow: [SKILL.md](SKILL.md)

Script interface reference (Chinese): [references/storage.md](references/storage.md)

```bash
python -m unittest discover -s tests -v
```

Tests cover incremental updates, no-op writes, preservation of existing content, nine-to-ten-column migration, notes, escaping, concurrency conflicts, and mocked media downloads. `media.py` downloads direct media files; screenshot capture is handled by the agent's environment tools. Mock tests do not validate live websites or application interfaces.

### License

[MIT](LICENSE) applies to this repository's code and documentation. It does not grant rights to third-party website content, images, or videos.

---

## 中文介绍

**宝藏资源库：把随手发现的好工具，变成可检索、可更新、带图可看的个人资源库。**

宝藏资源库是一个用于 **Codex 等支持 Agent Skills 的智能体**的技能。提供网站名称、网址或应用名称，智能体即可按照统一流程检索资料、归纳功能与评价、保存多媒体，并将结果整理到本地 Markdown 表格中。

适合积累 AI 工具、设计资源、效率应用、开发工具，以及团队共享的软件参考清单。

### 核心功能与优势

| 功能 | 带来的价值 |
| --- | --- |
| **多种输入，批量整理** | 接收一个或多个名称、网址、App 或桌面软件名称，减少逐个搜索、复制和整理的重复工作。 |
| **介绍与口碑分开整理** | 结合官方资料、独立评测和用户反馈，分别总结产品能力与使用评价；资料不足时明确说明，帮助判断工具是否适合自己。 |
| **统一格式，方便比较** | 固定十列，每项资源五个标签；介绍不超过 200 字，评价为不超过 150 字的一句话，便于快速浏览和关键词检索。 |
| **持续更新，避免重复收录** | 根据产品身份识别重复：新资源追加，有实质变化更新原行，没有变化不写入，让清单随使用逐步积累。 |
| **图片、视频与截图留在本地** | 优先下载官方媒体；无法保存时，尝试截取首页及关键功能页合计 1～3 张，方便回顾界面与用途。 |
| **异常透明，不悄悄丢失网址** | 官网无法核验时仍保留实际找到的地址，并注明“网址未验证”；访问报错、下载失败等情况写入备注，方便后续复查。 |
| **本地 Markdown，便于迁移** | 文档和素材由你保管，可放进 Obsidian 或其他支持 Markdown 表格的工具；使用相对路径关联素材，便于一起备份和移动。 |
| **兼顾已有文档** | 普通文档只在末尾追加资源表，维护已有资源库时保留无关内容；写入前检查文件版本，检测并发修改时停止覆盖。 |

### 会得到什么？

只生成表格，不添加资源库标题。固定字段为：

**名称｜官方网址｜介绍｜评价｜类型｜标签｜下载方式｜多媒体资料｜更新时间｜备注**

多媒体单元格可显示本地图片、截图及视频文件链接。素材默认保存在文档旁的 `<文档名>_素材/<资源标识>/`。没有采集异常时备注留空；无法下载或截图时，保留可核验的来源链接并说明原因。

### 安装与使用

将本仓库克隆或解压到 Codex 个人技能目录的 `treasure-resource-library` 文件夹，确保以下文件存在：

```text
~/.codex/skills/treasure-resource-library/SKILL.md
```

设置了 `CODEX_HOME` 时，使用其下的 `skills/treasure-resource-library`。保留 `agents/`、`references/`、`scripts/` 目录。其他兼容客户端按其技能安装方式配置，并确认具备下文列出的工具。

调用示例：

```text
请使用 $treasure-resource-library 整理 Notion、Obsidian 和 https://reactbits.dev/。
```

每次任务都会确认存储路径；本次请求已经提供路径时直接采用。

- **指定文件夹**：创建或维护其中的 `宝藏资源库.md`。
- **指定 Markdown 文件**：识别并维护其中的资源表，普通文档则在末尾追加。
- **再次提交已有资源**：比对资料，仅更新实质变化及更新时间。

### 运行条件与边界

- 需要支持该技能格式的智能体，以及网络搜索、网页读取工具；本技能不是独立后台采集服务。
- Python **3.10+**，辅助脚本仅依赖标准库，无需额外 Python 包。
- 截图依赖当前环境提供可导出图片的浏览器或应用截图工具；不会自动安装目标应用、绕过登录或保证所有页面可截取。
- 默认以中文整理；链接核验反映采集当时的结果，不保证永久可用。
- Markdown 保留隐藏维护标记。Obsidian 建议使用实时预览或阅读视图；源码模式会显示竖线和标记。移动文档时请同时移动素材目录。

### 开发与验证

完整工作流：[SKILL.md](SKILL.md)

脚本接口：[references/storage.md](references/storage.md)

```bash
python -m unittest discover -s tests -v
```

测试覆盖去重更新、无变化不写入、原文保护、九列到十列迁移、备注、字符转义、并发冲突和模拟媒体下载。`media.py` 负责直接媒体下载；截图由智能体调用环境工具完成。模拟测试不代表已验证真实网站或应用界面。

### 许可证

[MIT](LICENSE)。适用于仓库代码与说明，不授予第三方网站内容、图片或视频的版权许可。
