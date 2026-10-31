"""Collect one scoped read-only evidence source per invocation."""
import argparse
from common import RESOURCES, emit, get_resources, kubectl, redact


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--context", required=True)
    p.add_argument("--namespace", required=True)
    p.add_argument("--resource", choices=sorted(RESOURCES), default="pods")
    p.add_argument("--name")
    p.add_argument("--selector")
    p.add_argument("--field-selector")
    p.add_argument("--logs", action="store_true", help="Opt-in: logs may contain sensitive data")
    p.add_argument("--container")
    p.add_argument("--previous", action="store_true")
    args = p.parse_args()
    if args.logs:
        if not args.name or not args.container or args.resource != "pods":
            p.error("logs require --resource pods --name POD --container CONTAINER")
        if any(x.startswith("-") or "/" in x for x in (args.name, args.container)):
            p.error("invalid pod/container")
        cmd = ["logs", args.name, "--container", args.container, "--timestamps",
               "--since=30m", "--tail=200", "--limit-bytes=65536"]
        if args.previous:
            cmd.append("--previous")
        result = kubectl(args.context, args.namespace, cmd)
        result["output"] = redact(result.get("output", ""))
        result["source"] = {"context": args.context, "namespace": args.namespace,
                            "pod": args.name, "container": args.container,
                            "previous": args.previous, "window": "30m", "tail": 200}
        emit(result)
    else:
        emit(get_resources(args.context, args.namespace, args.resource, args.selector,
                           args.name, args.field_selector))


if __name__ == "__main__":
    main()
