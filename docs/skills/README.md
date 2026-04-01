# Aizen Skills Development Guide

## What are Skills?

Skills are reusable prompt templates and workflows that enhance Aizen Agent capabilities. They are stored in `~/.aizen/skills/` as Markdown files with YAML frontmatter.

## Skill Structure

```markdown
---
name: my-skill
description: What this skill does
category: development
triggers:
  - pattern: "build.*app"
  - pattern: "create.*project"
---

# My Skill

Instructions for the agent to follow...

## Steps

1. First step
2. Second step
3. Third step

## Pitfalls

- Common mistake 1
- Common mistake 2

## Examples

Example usage scenarios...
```

## Creating a Skill

### Method 1: CLI Command

```bash
aizen skills create my-skill
```

### Method 2: Manual Creation

1. Create directory: `mkdir -p ~/.aizen/skills/my-skill`
2. Create `SKILL.md` file
3. Add optional files in `templates/`, `scripts/`, `references/`

### Method 3: Save from Conversation

```
/save-skill my-skill
```

## Skill Categories

| Category | Purpose |
|----------|---------|
| `software-development` | Coding, debugging, testing |
| `devops` | Deployment, infrastructure, CI/CD |
| `mlops` | ML training, inference, evaluation |
| `research` | Papers, literature review, analysis |
| `creative` | Writing, art, music |
| `knowledge` | Memory, knowledge management |
| `workflow` | Process automation, orchestration |

## Skill Hooks

Skills can define hooks that run at specific points:

```yaml
hooks:
  pre_tool: |
    # Run before each tool call
    if tool_name == "terminal":
      validate_command(args["command"])
  post_tool: |
    # Run after each tool call
    log_result(result)
```

## Best Practices

1. **Be Specific**: Clear, actionable instructions
2. **Include Pitfalls**: Document common mistakes
3. **Provide Examples**: Show expected usage
4. **Use Categories**: Organize skills logically
5. **Version Control**: Track skill changes

## Skill API

### Loading a Skill

```python
from skills import load_skill

skill = load_skill("my-skill")
print(skill.name)        # "my-skill"
print(skill.description) # "What this skill does"
print(skill.content)     # Full markdown content
```

### Registering a Skill

```python
from skills import register_skill

register_skill(
    name="my-skill",
    content=skill_markdown,
    category="development",
)
```

### Listing Skills

```python
from skills import list_skills

for skill in list_skills():
    print(f"{skill.name}: {skill.description}")
```

## Example Skills

### Code Review Skill

```markdown
---
name: code-review
description: Perform thorough code review with security analysis
category: software-development
---

# Code Review

Perform a comprehensive code review covering:

## Checklist

- [ ] Code correctness
- [ ] Error handling
- [ ] Security vulnerabilities
- [ ] Performance issues
- [ ] Documentation
- [ ] Test coverage

## Output Format

```markdown
## Summary
Brief overview of changes

## Issues Found
- **Critical**: ...
- **Warning**: ...
- **Info**: ...

## Suggestions
- ...
```
```

### Debug Skill

```markdown
---
name: debug
description: Systematic debugging workflow
category: software-development
---

# Debug Workflow

## Steps

1. **Reproduce**: Verify the issue
2. **Isolate**: Find the failing component
3. **Hypothesize**: Form theories
4. **Test**: Validate hypotheses
5. **Fix**: Implement solution
6. **Verify**: Confirm fix works

## Debug Commands

```python
# Add debug logging
import logging
logging.basicConfig(level=logging.DEBUG)

# Profile performance
import cProfile
cProfile.run('problematic_function()')

# Memory analysis
import tracemalloc
tracemalloc.start()
```
```

## Installing Skills

From the skills registry:

```bash
aizen skills install git-workflow
aizen skills install mlops/training
```

From a URL:

```bash
aizen skills install https://example.com/skills/my-skill.md
```

## Sharing Skills

Skills are local-first, but you can share via:

1. **Git Repository**: Add to `.aizen/skills/` in your repo
2. **Gist**: Share as GitHub Gist
3. **File**: Copy SKILL.md directly

## See Also

- `/skills` - Browse available skills
- `/save-skill` - Save current workflow as skill
- `aizen skills --help` - CLI commands
