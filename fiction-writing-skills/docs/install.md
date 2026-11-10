# 安装与第一次使用

## Skill客户端

下载仓库后，完整复制所需技能目录，例如 `skills/fiction-scene-audit/` 到私人项目的 `.agents/skills/fiction-scene-audit/`。对于其他Agent Skills客户端，请按其技能发现规则选择目录。复制SKILL.md而不复制references会缺少契约和示例。不会替用户安装、覆盖既有技能或改全局配置。

在能访问私人材料的会话里明确调用 `$fiction-scene-audit`，指定有效正文、人物完整小节、关系/知识/能力来源、上一章结尾和批准大纲。普通聊天需要实际提供文件或内容，不能只贴本地路径。文件缺失时模型应列缺口，不能补造。

## 无Skill客户端

将所选SKILL.md作为工作说明，并提供它指向的references和实际输入。按Markdown步骤执行即可；Python不是使用技能的前提。普通聊天不保证自动加载技能或本地文件。

## Python工具

需要Python 3.10+，无需安装包；在仓库根执行README中的检查命令。`demo`在临时目录完成一次快照、核验和通过稿复制。不要对小说原目录运行旧项目脚本，本仓库也不包含它们。

## 私人写作目录建议

把canon、characters、abilities、outlines、chapters、reviews、state分别放在自己的目录。名称可自定，脚本通过显式相对路径定位文件。共享给外部写作者时，仅交付相关原始条目、输入版本及允许揭露范围；不要默认交出整个私人目录。

测试覆盖复制到临时路径和无第三方包的Python执行；未通过安装真实客户端自动发现来认证跨产品兼容。
