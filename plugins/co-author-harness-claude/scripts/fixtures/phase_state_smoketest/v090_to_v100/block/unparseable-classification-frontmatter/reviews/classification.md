---
manuscript_id: v090-to-v100-block-unparseable-classification
default_final_phase: Ph3
wiki_linked: true

# Classification — unparseable-classification-frontmatter

The YAML frontmatter is missing its closing `---` delimiter; the migration
must reject this with exit code 7 rather than silently falling through to
the markdown body.
