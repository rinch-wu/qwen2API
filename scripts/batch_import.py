#!/usr/bin/env python3
"""
qwen2API 账号批量导入脚本

用法：
  python batch_import.py                     # 交互式输入
  python batch_import.py --admin-key <key>    # 指定 admin key
  python batch_import.py --accounts "a@b:c\nd@e:f"  # 直接指定账号内容
"""

import argparse
import json
import urllib.request
import urllib.error


def batch_import(base_url: str, admin_key: str, accounts: str) -> dict:
    """
    调用 /api/admin/accounts/batch 批量导入账号

    参数：
        base_url:  服务地址，例如 http://127.0.0.1:7870
        admin_key:  管理员密钥（ADMIN_KEY 环境变量对应的值）
        accounts:   多行字符串，每行格式 email:password
    """
    url = f"{base_url.rstrip('/')}/api/admin/accounts/batch"
    payload = json.dumps({"content": accounts}).encode("utf-8")

    req = urllib.request.Request(
        url,
        data=payload,
        headers={
            "Authorization": f"Bearer {admin_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8")
        raise RuntimeError(f"HTTP {e.code}: {body}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"连接失败: {e.reason}") from e


def interactive_mode(base_url: str, admin_key: str):
    print("=" * 50)
    print("  qwen2API 批量导入账号")
    print("  格式：每行一个账号，email:password")
    print("  输入空行结束输入")
    print("=" * 50)
    print()

    lines = []
    while True:
        try:
            line = input("> ").strip()
        except EOFError:
            break
        if not line:
            break
        lines.append(line)

    if not lines:
        print("未输入任何账号，退出。")
        return

    content = "\n".join(lines)
    print(f"\n正在导入 {len(lines)} 个账号...\n")

    result = batch_import(base_url, admin_key, content)
    print("结果：")
    print(json.dumps(result, ensure_ascii=False, indent=2))

    if result.get("ok"):
        print(f"\n✅ 成功 {result['added']} 个，失败 {result['failed']} 个")
        if result.get("errors"):
            print("失败详情：")
            for err in result["errors"]:
                print(f"  第 {err['line']} 行：{err['error']}")
    else:
        print("\n❌ 批量导入失败")


def main():
    parser = argparse.ArgumentParser(description="qwen2API 批量导入账号")
    parser.add_argument("--base-url", default="http://127.0.0.1:7870",
                        help="服务地址（默认 http://127.0.0.1:7870）")
    parser.add_argument("--admin-key", default="admin",
                        help="管理员密钥（默认 admin）")
    parser.add_argument("--accounts", default=None,
                        help="直接指定账号内容，格式：a@b:c\\nd@e:f")

    args = parser.parse_args()

    if args.accounts:
        print(f"正在导入...\n")
        result = batch_import(args.base_url, args.admin_key, args.accounts)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        print(f"\n✅ 成功 {result.get('added', 0)} 个，失败 {result.get('failed', 0)} 个")
    else:
        interactive_mode(args.base_url, args.admin_key)


if __name__ == "__main__":
    main()
