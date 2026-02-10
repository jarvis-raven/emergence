"""Entry point for python3 -m core.memory"""
import sys

if len(sys.argv) < 2:
    print("Usage: python3 -m core.memory <command>")
    print("Commands: consolidate, nightly, self-history, flush-prompt")
    sys.exit(1)

cmd = sys.argv[1]
sys.argv = sys.argv[1:]  # shift args

if cmd == "consolidate":
    from .consolidation import main
    main()
elif cmd == "nightly":
    from .nightly_build import main
    main()
elif cmd == "self-history":
    from .self_history import main
    main()
elif cmd == "flush-prompt":
    from .flush_prompt import main
    main()
else:
    print(f"Unknown command: {cmd}")
    sys.exit(1)
