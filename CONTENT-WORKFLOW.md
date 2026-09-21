# IC Eight content update workflow

Article bodies remain ordinary static HTML. `articles.json` is the single editorial registry used to build the site's article indexes.

For a new article:

1. Add the finished HTML file at its public path. Copy the canonical `<nav>` from `index.html`; the validation step rejects missing or stale article navigation.
2. Add one entry to `articles.json` with `tag`, `contentType`, `title`, `url`, `description`, and `publishedAt`. Put a newly published article at the beginning of the file so the visible article index remains newest-first. Use `"contentType": "article"` for ordinary articles and `"contentType": "pve"` for every PVE-series item.
3. Every PVE-series item must also have `pveRoles`. Numbered evaluations use `["evaluation"]`; the initial Chance pilot uses `["pilot"]`; Reevo uses `["extra"]`; Research Notes use `"research-note"`; and follow-ups use `"follow-up"`. Multiple roles are allowed.
4. A primary Product Value Evaluation also keeps its existing `pve` block. Copy an existing numbered PVE entry as the template and give it a unique `id` and `order`.
5. A follow-up must add `parentPveIds` naming its parent section. A cross-PVE Research Note adds `"cross-pve-synthesis"` to `pveRoles` instead. Keep `tag` as the separate topic classification.
6. Run:

   ```bash
   python3 scripts/build-content-indexes.py
   python3 scripts/build-content-indexes.py --check
   ```

The generator updates the JavaScript-free article list in `articles.html`, the cards and count in `product-value-evaluations.html`, `rss.xml`, and the article URLs in `sitemap.xml`. The PVE overview page reads its latest four cards from the generated library automatically.

GitHub Pages also runs the generator during deployment, so the published site is rebuilt from the registry even if the local generation step was forgotten. Running it locally is still recommended so the preview and committed generated files match production.

If the registry contains a duplicate URL, duplicate title, duplicate PVE ID, missing or unknown content metadata, an invalid or duplicated PVE role, a follow-up without a valid parent PVE, a missing article file, article navigation that differs from `index.html`, an invalid publication timestamp, or a PVE card pointing to an unregistered article, generation stops without updating the derived files.
