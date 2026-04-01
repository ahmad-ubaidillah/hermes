#!/usr/bin/env python3
"""
Aizen Memory CLI - Manage memories from command line.

Usage:
    aizen memory add <content> [--static] [--days=N]
    aizen memory list [--all]
    aizen memory search <query>
    aizen memory profile
    aizen memory stats
    aizen memory forget <id>
    aizen memory update <id> <new_content>
    aizen memory clear [--all]
"""

import sys
import argparse
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from knowledge.memory_store import MemoryStore, MemoryType


def main():
    parser = argparse.ArgumentParser(
        description="Aizen Memory Management",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Commands")
    
    # Add command
    add_parser = subparsers.add_parser("add", help="Add a memory")
    add_parser.add_argument("content", help="Memory content")
    add_parser.add_argument("--static", action="store_true", help="Permanent memory")
    add_parser.add_argument("--days", type=int, help="Days until expiration")
    add_parser.add_argument("--tag", default="default", help="Container tag")
    
    # List command
    list_parser = subparsers.add_parser("list", help="List memories")
    list_parser.add_argument("--all", action="store_true", help="Include forgotten")
    list_parser.add_argument("--tag", default="default", help="Container tag")
    list_parser.add_argument("--limit", type=int, default=50, help="Max results")
    
    # Search command
    search_parser = subparsers.add_parser("search", help="Search memories")
    search_parser.add_argument("query", help="Search query")
    search_parser.add_argument("--tag", default="default", help="Container tag")
    search_parser.add_argument("--limit", type=int, default=10, help="Max results")
    
    # Profile command
    profile_parser = subparsers.add_parser("profile", help="Show memory profile")
    profile_parser.add_argument("--tag", default="default", help="Container tag")
    
    # Stats command
    stats_parser = subparsers.add_parser("stats", help="Show memory statistics")
    stats_parser.add_argument("--tag", default="default", help="Container tag")
    
    # Forget command
    forget_parser = subparsers.add_parser("forget", help="Forget a memory")
    forget_parser.add_argument("id", help="Memory ID")
    forget_parser.add_argument("--reason", default="manual", help="Reason")
    
    # Update command
    update_parser = subparsers.add_parser("update", help="Update a memory")
    update_parser.add_argument("id", help="Memory ID")
    update_parser.add_argument("content", help="New content")
    
    # Clear command
    clear_parser = subparsers.add_parser("clear", help="Clear memories")
    clear_parser.add_argument("--all", action="store_true", help="Include static")
    clear_parser.add_argument("--tag", default="default", help="Container tag")
    
    # Inject command
    inject_parser = subparsers.add_parser("inject", help="Format for injection")
    inject_parser.add_argument("--tag", default="default", help="Container tag")
    inject_parser.add_argument("--query", help="Search query")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    store = MemoryStore(container_tag=getattr(args, "tag", "default"))
    
    if args.command == "add":
        memory = store.add(
            content=args.content,
            is_static=args.static,
            forget_after_days=args.days,
        )
        type_str = "static" if args.static else "dynamic"
        print(f"Added {type_str} memory: {memory.id}")
        print(f"  Content: {memory.content}")
        if args.days:
            print(f"  Expires: {args.days} days")
    
    elif args.command == "list":
        memories = store.list_all(include_forgotten=args.all, limit=args.limit)
        print(f"\n{'Memories' if not args.all else 'All Memories'} ({len(memories)}):\n")
        for m in memories:
            type_str = "[S]" if m.memory_type == MemoryType.STATIC else "[D]"
            forgot = " [FORGOTTEN]" if m.is_forgotten else ""
            print(f"  {type_str} {m.id[:8]}... | {m.content[:60]}{forgot}")
        print()
    
    elif args.command == "search":
        memories = store.search(args.query, limit=args.limit)
        print(f"\nSearch results for '{args.query}' ({len(memories)}):\n")
        for m in memories:
            print(f"  {m.id[:8]}... | {m.content[:60]}")
        print()
    
    elif args.command == "profile":
        profile = store.get_profile()
        print("\n" + profile.to_markdown() + "\n")
    
    elif args.command == "stats":
        stats = store.stats()
        print(f"\nMemory Statistics:")
        print(f"  Total:     {stats['total']}")
        print(f"  Static:    {stats['static']}")
        print(f"  Dynamic:   {stats['dynamic']}")
        print(f"  Forgotten: {stats['forgotten']}")
        print()
    
    elif args.command == "forget":
        store.forget(args.id, args.reason)
        print(f"Forgot memory: {args.id}")
    
    elif args.command == "update":
        memory = store.update(args.id, args.content)
        print(f"Updated memory: {memory.id} (v{memory.version})")
        print(f"  Content: {memory.content}")
    
    elif args.command == "clear":
        deleted = store.clear(include_static=args.all)
        what = "all" if args.all else "dynamic"
        print(f"Cleared {deleted} {what} memories")
    
    elif args.command == "inject":
        context = store.format_for_injection(query=args.query)
        print(context)
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
