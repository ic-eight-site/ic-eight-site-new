# IC Eight content update workflow

Article bodies remain ordinary static HTML. `articles.json` is the single editorial registry used to build the site's article indexes.

For a new article:

1. Add the finished HTML file at its public path.
2. Add one entry to `articles.json` with `tag`, `title`, `url`, `description`, and `publishedAt`. Put a newly published article at the beginning of the file so the visible article index remains newest-first.
3. For a Product Value Evaluation, add its `pve` block to that same entry. Copy an existing numbered PVE entry as the template and give it a unique `id` and `order`.
4. Run:

   ```bash
   python3 scripts/build-content-indexes.py
   python3 scripts/build-content-indexes.py --check
   ```

The generator updates the JavaScript-free article list in `articles.html`, the cards and count in `product-value-evaluations.html`, `rss.xml`, and the article URLs in `sitemap.xml`. The PVE overview page reads its latest four cards from the generated library automatically.

GitHub Pages also runs the generator during deployment, so the published site is rebuilt from the registry even if the local generation step was forgotten. Running it locally is still recommended so the preview and committed generated files match production.

If the registry contains a duplicate URL, duplicate title, duplicate PVE ID, unknown category, missing article file, invalid publication timestamp, or PVE card pointing to an unregistered article, generation stops without updating the derived files.
