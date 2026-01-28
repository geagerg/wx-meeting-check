# 企业微信会议汇总

获取指定成员“今天/明天”的会议列表，拉取会议详情后汇总成文本，通过 webhook 发送到群里。

## 文件说明
- `get_access_token.py`：获取 access_token + 本地缓存
- `meeting_report.py`：主流程（拉会议、取详情、发 webhook）
- `config_example.json`：配置模板

## 配置
1) 复制 `config_example.json` 为 `config.json`
2) 填写字段：
   - `corpid`：企业 ID
   - `corpsecret`：应用密钥
   - `userid`：目标成员 ID
   - `webhook_url`：群机器人 webhook
   - `token_cache_file`：token 缓存文件路径（默认 `token_cache.json`）

## 运行
```powershell
python .\meeting_report.py
# 或
python .\meeting_report.py .\config.json
```

## 输出
发送到群里的内容包含：
- 今日会议数量 + 列表（格式：`HH:MM 标题`）
- 明日会议数量 + 列表（格式：`HH:MM 标题`）

## 常见问题
- 如果报 `errcode: 48002`，通常是应用没有会议接口权限或 IP 白名单未放行。
