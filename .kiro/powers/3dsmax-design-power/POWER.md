---
name: "3dsmax-design-power"
displayName: "3ds Max Design Power"
description: "Structured design assistant for 3ds Max and V-Ray features in Deadline Cloud. Creates comprehensive design documents covering data structures, UX changes, job templates, and adapter modifications."
keywords: ["3dsmax", "vray", "design", "maxscript", "pymxs"]
author: "AWS Deadline Cloud Team"
---

# 3ds Max Design Power

## Overview

A structured design assistant for creating comprehensive feature designs for 3ds Max and V-Ray integration with AWS Deadline Cloud. This power helps create well-structured design documents following a consistent four-section format that covers all aspects of implementation.

## Code Snippet Style Guide

When including code in design documents, use **concise inline snippets** in the main sections and put **full implementations in an appendix**.

### Inline Code Format

Show only the relevant changes with context:

```python
def existing_function():
    ...existing logic...
    
    # NEW: Add feature X support
    if feature_x_enabled:
        self._configure_feature_x(data)
    
    ...rest of function...
```

### Appendix Format

Put complete implementations in a clearly marked appendix section:

```markdown
---

## Appendix: Full Code Implementations

<!-- REVIEW: New export_vrscene implementation -->

### A.1 VrayHandler.export_vrscene (Full Implementation)

\`\`\`python
def export_vrscene(self, data: dict) -> None:
    """Full implementation here..."""
    # Complete code
\`\`\`
```

### Guidelines

1. **Data structures are the exception**: Always show full definitions - they anchor the design
2. **Other sections**: Show what changes and where, not full implementations
3. **Use `...` or comments** to indicate existing/unchanged code
4. **Flag new sections** with `<!-- REVIEW: description -->` comments in the appendix
5. **Don't include review tags** in final generated code

## MCP Tools

This power includes the **Autodesk Product Help MCP** server (`autodesk-product-help`), which provides direct access to Autodesk's official documentation for 110+ products including 3ds Max, V-Ray, and MAXScript.

Use it to:
- Research 3ds Max SDK/MAXScript APIs during design work
- Look up V-Ray render settings, parameters, and scripting interfaces
- Find official Autodesk documentation for feature design references

The server exposes two tools:
- `get_available_products` - List all supported Autodesk products and their release codes
- `search_help_content` - Search Autodesk documentation by product, release, and query

When searching, use product code `3DSMAX` for 3ds Max documentation.

## Research Requirements

Before finalizing any design, research 3ds Max/V-Ray APIs, Deadline 10 implementation, and internet sources. Use the Autodesk Product Help MCP to look up official documentation. Refer to **research-guide.md** for details.

## Key Technical Patterns

Refer to **research-guide.md** for pymxs/MAXScript patterns, V-Ray renderer detection, and settings access.

## External References

Refer to **external-references.md** for GitHub discussions and documentation links.