# 改写规则 · 判定口径与边界

本文件说明 `skill_publish_check.py` 的完整规则、自定义配置格式、误报处理与已知边界。

## 1. 收集的语义

暂存副本只复制「发布器实际会收进包」的文件。跳过：

- 目录：`.git` `.idea` `.vscode` `node_modules` `__pycache__` `.pytest_cache` `tmp` `outputs` `models` `venv` `.venv` `__MACOSX`
- 后缀：`.pyc` `.DS_Store` `.tmp` `.log` `.lock` `.pid` `.session` `.swp` `.jsonl` 等运行态产物
- 平台元数据：`_meta.json` `_skillhub_meta.json` `_knot_meta.json` `.skillhubignore`
- 软连接：一律跳过

这样保证「扫描的对象」与「真正会发布出去的文件」一致，不会对不进包的文件误报。

## 2. 环境路径改写规则（sanitize 时应用）

| 规则名 | 命中形态（示例） | 改写为 |
|---|---|---|
| `win_workbuddy` | `C:\Users\<用户名>\.workbuddy\skills\<技能名>` | `<你的技能目录>` |
| `posix_workbuddy` | `/Users/<用户名>/.workbuddy/skills/<技能名>` | `<你的技能目录>` |
| `tilde_workbuddy` | `~/.workbuddy/skills/<技能名>` | `<你的技能目录>` |
| `win_home` | `C:\Users\<用户名>\...` | `%USERPROFILE%\...` |
| `posix_home` | `/Users/<用户名>/...`、`/home/<用户名>/...` | `~/...` |
| `workspace_root` | `/Users/<用户名>/Downloads/<项目>/...` | `<你的项目目录>` |

顺序敏感：先匹配长规则（含 `.workbuddy` 的绝对路径），再匹配短规则（家目录），避免只替换一半。

**占位符的设计意图**：`<你的技能目录>` 这类尖括号写法一眼可见「需要读者修改」，比替换成某个假路径更好——读者不会误以为那是真实存在的路径。

## 3. README 维护者配置清理

三种删除机制：

1. **整节删除**：标题含「维护者 / 作者信息 / 作者配置 / 联系方式 / maintainer / author / contact」的章节，删到下一个同级或更高级标题前。
2. **字段行删除**：以「维护者: / 作者: / 邮箱: / 联系方式: / Maintainer: / Author: / Email:」开头的行。
3. **配置行删除**：含 `KEEPER_FORBID_ROOTS=`、`FORBID_ROOTS=`、`PUBLISH_CONFIG=`、`FORBIDDEN_ROOTS=` 的行。

另外支持显式标注：源 README 中用 `<!-- publish:remove -->被删内容<!-- /publish:remove -->` 包住的区块，sanitize 时整块移除。这是给维护者手动标记「这段绝不能公开」的逃生口。

## 4. 安全检查规则

### 硬问题（hard，阻断发布）

`sk-` OpenAI key、`gh[pousr]_` GitHub token、`xox[baprs]-` Slack token、`AIza` Google key、`AKIA` AWS key、`-----BEGIN ... PRIVATE KEY-----` 私钥块、JWT、`skh_` SkillHub token、`password/passwd/pwd =` 明文口令。

### 报警（warn，人工确认）

真实邮箱（qq/163/gmail/outlook 等）、家目录路径、`.workbuddy` / `.claude` 字样、内网主机名（`.internal/.corp/.local/.lan`）、公网 IP。

### 占位符豁免

命中文本含以下任一词时不计数：`placeholder` `example` `示例` `占位` `<...>` `{{...}}` `your_*` `xxx` `test@` `foo@` `user@` `localhost` `127.0.0.1` `10.x.x.x`。这样文档里的正常示例不会制造假红。

## 5. 自定义配置（--config）

JSON 格式，三个可选字段：

```json
{
  "extra_rewrites": [
    {
      "name": "公司名",
      "find": "内部代号[0-9]+",
      "replace": "<你的项目名>",
      "note": "把内部项目代号改成读者占位符"
    }
  ],
  "extra_forbidden": [
    "机密项目名",
    "customer-[0-9]+"
  ]
}
```

- `extra_rewrites.name`：规则名，出现在改写统计里。
- `extra_rewrites.find`：Python 正则，大小写不敏感。
- `extra_rewrites.replace`：替换文本，建议用尖括号占位符。
- `extra_forbidden`：命中的一律记为硬问题，阻断发布。

配置文件本身含维护者私有信息，**不要**放进待发布的 skill 目录，放在 skill 目录之外。

## 6. 误报处理

- 安全扫描命中但其实是文档示例 → 确认命中文本含占位词；否则用编辑工具改成 `example.com` / `<你的值>` 这类标准占位写法。
- 某个真实路径需要保留（例如公开示例必须指向某个固定路径）→ 在源文件里用尖括号包住可变部分，让豁免规则生效。
- 自定义规则误报 → 收紧正则，或把规则移出配置。

## 7. 已知边界

- 只处理文本文件的确定性改写，无法识别语义层面的业务指纹（客户名、内部项目代号、敏感业务上下文）。第 4 步人工复核不可省略。
- 正则无法覆盖所有密钥形态；新增 token 前缀请加入 `extra_forbidden`。
- `verify` 只读检查暂存副本，不会自动修复；发现问题要回到源文件处理后重新 sanitize。
- 二进制文件原样复制，不做内容扫描。
- 暂存目录必须在源目录之外且尚不存在（防止污染源目录或误覆盖）。
