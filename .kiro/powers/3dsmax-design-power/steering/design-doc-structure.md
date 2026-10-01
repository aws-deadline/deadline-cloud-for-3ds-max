---
inclusion: manual
---

# Design Document Structure

Every design document MUST follow this four-section structure:

## 1. Data Structures to Change or Add

Define all data model changes including:
- New dataclasses or TypedDicts
- Modifications to existing data structures
- Job parameter schemas
- Configuration objects
- Type annotations (use `Any` for pymxs objects)

## 2. UX Changes (Submitter Dialog)

Document all user-facing changes:
- New UI controls (dropdowns, checkboxes, text fields)
- Control placement and grouping
- Default values and validation
- Tooltips and help text
- Conditional visibility logic

## 3. Job Template and Bundle Changes

Specify modifications to:
- Job template YAML structure
- New parameters and their types
- Parameter dependencies and conditions
- Asset references and attachments

## 4. Adapter Server-Client Changes

Detail the runtime implementation:
- Handler modifications (DefaultMaxHandler, VrayHandler, etc.)
- New action handlers
- MaxClient changes
- Path mapping considerations
- pymxs/MAXScript API usage
