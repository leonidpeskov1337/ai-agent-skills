"""Allowlisted Argo evidence fields; never emit values, generators or manifests."""
from urllib.parse import urlsplit, urlunsplit


def safe_url(value):
    if not isinstance(value, str):
        return None
    if "://" not in value:
        return value.split("?", 1)[0].split("#", 1)[0]
    try:
        parts = urlsplit(value)
        host = parts.hostname
        if not host:
            return "[INVALID_URL]"
        if ":" in host:
            host = "[" + host + "]"
        if parts.port:
            host += ":" + str(parts.port)
        return urlunsplit((parts.scheme, host, parts.path, "", ""))
    except ValueError:
        return "[INVALID_URL]"


def only(value, keys):
    if not isinstance(value, dict):
        return {}
    return {key: value[key] for key in keys if key in value}


def source_pointer(source):
    source = source or {}
    safe = only(source, ("path", "chart", "targetRevision", "ref", "name"))
    if "repoURL" in source:
        safe["repoURL"] = safe_url(source["repoURL"])
    return safe


def application_spec(spec):
    spec = spec or {}
    safe = {"project": spec.get("project")}
    destination = spec.get("destination") or {}
    safe["destination"] = only(destination, ("name", "namespace"))
    if "server" in destination:
        safe["destination"]["server"] = safe_url(destination["server"])
    if "source" in spec:
        safe["source"] = source_pointer(spec["source"])
    if "sources" in spec:
        safe["sources"] = [source_pointer(source) for source in spec["sources"] or []]
    policy = spec.get("syncPolicy") or {}
    if "automated" in policy:
        automated = policy["automated"]
        safe["automated"] = (only(automated, ("enabled", "prune", "selfHeal", "allowEmpty"))
                             if isinstance(automated, dict) else automated)
    return safe


def resource_result(resource):
    safe = only(resource, ("group", "version", "kind", "namespace", "name", "status",
                          "message", "hookType", "hookPhase", "syncPhase", "requiresPruning"))
    if isinstance(resource.get("health"), dict):
        safe["health"] = only(resource["health"], ("status", "message"))
    return safe


def project_argo(item):
    meta, spec, status = (item.get(key) or {} for key in ("metadata", "spec", "status"))
    safe = {"kind": item.get("kind"), "name": meta.get("name"), "namespace": meta.get("namespace"),
            "uid": meta.get("uid"), "generation": meta.get("generation"),
            "owners": meta.get("ownerReferences", []), "created": meta.get("creationTimestamp")}
    safe_status = only(status, ("reconciledAt", "observedAt", "conditions", "controllerNamespace"))
    if item.get("kind") == "ApplicationSet":
        safe["generator_types"] = [sorted(generator.keys()) for generator in spec.get("generators") or []]
        safe["template"] = application_spec((spec.get("template") or {}).get("spec"))
    else:
        safe["spec"] = application_spec(spec)
        safe_status["sync"] = only(status.get("sync", {}), ("status", "revision", "revisions"))
        safe_status["health"] = only(status.get("health", {}), ("status", "message", "lastTransitionTime"))
        safe_status["resources"] = [resource_result(resource) for resource in status.get("resources") or []]
        safe_status["history"] = [only(entry, ("id", "revision", "revisions", "deployedAt", "deployStartedAt"))
                                    for entry in status.get("history") or []]
        operation = status.get("operationState") or {}
        safe_operation = only(operation, ("phase", "message", "startedAt", "finishedAt"))
        sync_result = operation.get("syncResult") or {}
        safe_operation["syncResult"] = only(sync_result, ("revision", "revisions"))
        safe_operation["syncResult"]["resources"] = [resource_result(resource)
                                                     for resource in sync_result.get("resources") or []]
        safe_status["operationState"] = safe_operation
    safe["status"] = safe_status
    return safe
