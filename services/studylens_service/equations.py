"""Conservative OMML structure preview. No evaluation or inferred missing symbols."""
M = "{http://schemas.openxmlformats.org/officeDocument/2006/math}"


def equation_preview(node, depth=0):
    if depth > 20:
        return {"kind": "unsupported"}
    name = node.tag.removeprefix(M)
    if not node.tag.startswith(M):
        return {"kind": "unsupported"}
    if name == "t":
        return {"kind": "text", "text": node.text or ""}
    if name.endswith("Pr"):
        return None  # Presentation properties are not formula operands.
    if name in ("f", "sSup", "sSub", "sSubSup"):
        names = {"f": ("num", "den"), "sSup": ("e", "sup"), "sSub": ("e", "sub"), "sSubSup": ("e", "sub", "sup")}[name]
        children = [node.find(M + item) for item in names]
        if any(item is None for item in children):
            return {"kind": "unsupported"}
        return {"kind": {"f": "fraction", "sSup": "sup", "sSub": "sub", "sSubSup": "subsup"}[name],
            "children": [equation_preview(item, depth + 1) for item in children]}
    if name in ("oMath", "num", "den", "e", "sup", "sub", "r"):
        children = [equation_preview(item, depth + 1) for item in node]
        return {"kind": "row", "children": [item for item in children if item is not None]}
    return {"kind": "unsupported"}  # Matrices, radicals, integrals etc require a fuller renderer.


def preview_supported(node):
    return node is not None and node["kind"] != "unsupported" and all(preview_supported(child) for child in node.get("children", []))
