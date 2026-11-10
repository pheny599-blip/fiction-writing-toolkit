# 文件工具契约

Python 3.10+，只用标准库。所有输出拒绝覆盖，输入路径显式指定，不自动扫描私人目录。错误返回退出码1，不把失败记录为通过。`--root`可为任意用户工作区；工作区内文件路径必须使用相对路径和正斜线，不含父级跳转、冒号或符号链接。普通输入目录应由单一编辑者控制；工具不提供进程锁或对抗并发篡改的安全边界。

## 快照

```sh
python scripts/fiction_tools.py snapshot --root MY_PRIVATE_WORKSPACE --output SNAPSHOT_OUTPUT canon.md characters.md outline.md approval.json
python scripts/fiction_tools.py verify --root MY_PRIVATE_WORKSPACE --snapshot SNAPSHOT_OUTPUT
```

把大写路径参数替换为实际位置；输出父目录需已存在。快照逐项记录相对路径和SHA256。verify核对显式输入未变化；缺失、重复、空快照、路径逃逸或哈希不符均失败。

## 审查通过稿固定

1. 从[批准记录模板](../templates/approval.json)填写实际作者确认依据与批准大纲SHA256。默认pending不放行；演示批准不能用于真实稿件。
2. 在私人目录快照列入所有适用原始依据、大纲和approval.json，不包括候选/报告等输出。快照本身固定保存。批准记录须在快照前建立。
3. 完成实际语义审查，填写[报告模板](../templates/review.json)。将实际候选、大纲、快照的SHA256写入绑定字段。coverage八项每项用checked或有理由的not-applicable，并填来源/位置等证据；缺失不能冒填checked。报告适用的稿件或来源变更后要重新审查，不能只刷新哈希。
4. issues保持稳定ID；severity为blocking、required、optional，status为open或resolved。阻断和必要修改必须resolved且有复审证据；可选建议可open。初审round=0，默认返修轮次1—3。工具不保存上一轮历史，不能检测伪造轮数或身份；作者必须保留实际进度及报告。
5. 从[任务绑定模板](../templates/job.json)填写五个文件的路径和实际SHA256，然后执行：

```sh
python scripts/fiction_tools.py finalize --root MY_PRIVATE_WORKSPACE --job JOB_FILE --output reviewed-v1.md
```

`--job`是实际JSON文件位置；`--output`相对root，父目录须存在。五个文件必须互不相同，批准绑定确切大纲，报告绑定确切候选/大纲/快照。通过时原样复制候选并核对字节。不会生成作者审美接受记录、自动写正史或公开发布。章末状态由Skill从正文另行整理。模板默认空字段和incomplete，不能直接当真实通过报告。

`python scripts/fiction_tools.py demo`用临时合成声明演示机械链，不代表模型审稿。真实小场景演练见[记录](../examples/harbor/MODEL_REVIEW.md)。

## 仓库验证与发布目录

`python scripts/validate_repo.py`核对本项目最小Skill元数据、名称、内部引用、独立目录引用、Python语法、JSON、白名单集合及常见敏感模式。它不是完整YAML解析器或通用Agent Skills认证器，也不能证明零原创内容泄露。

`python scripts/build_release.py --output RELEASE_DIRECTORY --hash-report HASH_REPORT_FILE`在全新、位于源仓库之外的目录中构建白名单文件，并在另一个新文件写文件名/字节数/SHA256，供作者确认。已有目录、未知文件、路径逃逸及符号链接均拒绝。不执行Git提交、联网或推送。使用者修改白名单前须人工审查新增文件，程序不会自动批准它们。
