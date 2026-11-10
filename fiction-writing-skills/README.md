# Fiction Writing Skills

把长篇小说的设定、人物、情节和审稿交接变成可追踪的文件工作流。适合已有少量设定或稿件、希望减少长篇连续性错误的作者；玄幻、仙侠、奇幻和科幻均可自行配置。

本项目提供5个Markdown Skill、2条组合工作流、通用模板、一个全新短例和Python标准库辅助工具。它来自真实创作流程的方法提炼，不包含来源小说、人物、能力、章节或聊天记录。

## 从零开始

1. 获取本仓库目录。需要运行脚本时准备Python 3.10或更高版本，无需pip依赖。
2. 在仓库根执行 `python scripts/validate_repo.py` 和 `python -m unittest discover -s tests -v`。
3. 在仓库之外建立自己的私人写作目录；不要把稿件存进本项目的发布目录。
4. 选择下面一项Skill，将其整个文件夹复制到支持Agent Skills的客户端技能目录。Codex可使用目标项目的 `.agents/skills/`，也可使用用户级技能目录。手动普通聊天使用时，提供SKILL.md及其实际需要的references文件和你的输入材料。路径文字不代表模型能读取文件。
5. 从 [外部写作与审稿](workflows/external-draft-review.md) 开始。没有独立Agent时仍可使用，但必须说明是单端审查。

只复制一个Skill目录也能使用：每项技能的模板和示例都在它自己的references内。无需安装其余四项；仓库Python工具是可选辅助。

## 模块与调用

|模块|解决的问题|调用例|
|---|---|---|
|[fiction-canon](skills/fiction-canon/SKILL.md)|已确认规则、计划、角色猜测分层；关系/知识/能力边界|`使用 $fiction-canon，整理这些设定；把计划与事实分开，不补造缺失机制。`|
|[fiction-outline](skills/fiction-outline/SKILL.md)|从前文后果构造人物选择与事件因果|`使用 $fiction-outline，为下一章拟大纲，保留禁揭信息，先交具体版本给我确认。`|
|[fiction-scene-audit](skills/fiction-scene-audit/SKILL.md)|人物、关系、知情、动作与场景因果集中审查|`使用 $fiction-scene-audit，审查指定稿件；按原文证据列问题，不改全文。`|
|[fiction-voice-revision](skills/fiction-voice-revision/SKILL.md)|依据作者样本和本轮目标局部修订，防止事实偏移|`使用 $fiction-voice-revision，只修指定段落，保留能力代价和未知状态。`|
|[fiction-chapter-closeout](skills/fiction-chapter-closeout/SKILL.md)|固定通过稿、生成有证据的章末状态、断点恢复|`使用 $fiction-chapter-closeout，核对稿件与报告绑定，生成下一章交接，不续写。`|

通用[阶段角色提示](templates/role-prompts.md)可按需组合。可选[阶段分工工作流](workflows/staged-chapter.md)是执行协议，未提供自动调度服务。

## 可运行的工具

```sh
python scripts/fiction_tools.py snapshot --root examples/harbor --output /tmp/harbor-snapshot.json canon.md characters.md outline.md approval.md
python scripts/fiction_tools.py verify --root examples/harbor --snapshot /tmp/harbor-snapshot.json
python scripts/fiction_tools.py demo
python scripts/build_release.py --output /tmp/fiction-writing-skills-release
```

Windows把 `/tmp/...` 换成现有父目录中的自选输出路径。所有输出拒绝覆盖；demo使用系统临时目录自行清理。`finalize`的完整契约见[脚本说明](docs/tools.md)。脚本只能检查输入是否齐备、字节哈希和声明的审查状态，不能判断小说好坏或证明作者真的批准。

## 兼容性与限制

- 技能采用Agent Skills最小格式（name、description），不绑定特定模型/API，不发消息、不联网、不自动改正史。客户端发现方式不同，具体安装见[安装说明](docs/install.md)。
- 审稿是模型或人工判断，可能耗时/产生模型费用；没有AI检测百分比、自动世界生成器、RAG记忆、Word导出或能力平衡引擎。
- 证据不足应交付缺口而非“通过”。三轮返修上限是默认止损参数，可由作者为项目明确调整；不能通过重启任务暗中清零。
- 测试范围与未验证项见[测试报告](docs/TEST_RESULTS.md)。尚未验证所有客户端自动发现及真实长篇使用效果。

## 许可与维护

本仓库中列入[发布白名单](release-allowlist.json)的新写工具、文档与演示以MIT发布。许可证不扩展到任何外部小说、作者输入、私人交接、第三方素材或生成服务条款；使用工具不会要求你开源自己的作品。见[许可范围](docs/licensing.md)、[维护规则](docs/MAINTENANCE.md)及[发布审查](PUBLICATION_REVIEW.md)。
