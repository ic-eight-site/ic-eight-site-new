#!/usr/bin/env ruby
# Keep the public site navigation identical across top-level pages and articles.

ROOT = File.expand_path('..', __dir__)

NAVIGATION = <<~HTML.chomp
  <nav class="site-header" aria-label="Primary navigation">
    <a href="/" class="nav-logo" aria-label="IC Eight shared entrance">IC Eight</a>
    <div class="primary-nav">
      <details class="nav-menu" data-nav-menu="buyer">
        <summary>Buyers &amp; Evaluators</summary>
        <div class="nav-dropdown">
          <a href="/buyer-evaluator.html" data-nav-path data-nav-section="buyer">Buyer / Evaluator Home</a>
          <a href="/product-decision-review.html" data-nav-path data-nav-section="buyer">Product Decision Review</a>
        </div>
      </details>
      <details class="nav-menu" data-nav-menu="product">
        <summary>Product Teams</summary>
        <div class="nav-dropdown">
          <a href="/product-team.html" data-nav-path data-nav-section="product">Product Team Home</a>
          <a href="/product-value-evaluation.html" data-nav-path data-nav-section="product">Evaluation</a>
          <a href="/product-value-diagnosis.html" data-nav-path data-nav-section="product">Diagnosis</a>
          <a href="/services.html" data-nav-path data-nav-section="product">Method</a>
        </div>
      </details>
      <a class="nav-link" href="/product-value-evaluations.html" data-nav-path>PVE Library</a>
      <a class="nav-link" href="/articles.html" data-nav-path>Insights</a>
      <a class="nav-link" href="/about.html" data-nav-path>About</a>
      <a class="nav-link" href="/contact.html" data-nav-path>Contact</a>
    </div>
    <details class="mobile-nav">
      <summary>Menu</summary>
      <div class="mobile-panel">
        <p class="mobile-group">Buyers &amp; Evaluators</p>
        <a href="/buyer-evaluator.html" data-nav-path data-nav-section="buyer">Buyer / Evaluator Home</a>
        <a href="/product-decision-review.html" data-nav-path data-nav-section="buyer">Product Decision Review</a>
        <p class="mobile-group">Product Teams</p>
        <a href="/product-team.html" data-nav-path data-nav-section="product">Product Team Home</a>
        <a href="/product-value-evaluation.html" data-nav-path data-nav-section="product">Evaluation</a>
        <a href="/product-value-diagnosis.html" data-nav-path data-nav-section="product">Diagnosis</a>
        <a href="/services.html" data-nav-path data-nav-section="product">Method</a>
        <div class="mobile-divider"></div>
        <a href="/product-value-evaluations.html" data-nav-path>PVE Library</a>
        <a href="/articles.html" data-nav-path>Insights</a>
        <a href="/about.html" data-nav-path>About</a>
        <a href="/contact.html" data-nav-path>Contact</a>
      </div>
    </details>
  </nav>
HTML

paths = Dir[File.join(ROOT, '*.html')] + Dir[File.join(ROOT, 'articles', '*.html')]
updated = 0

paths.sort.each do |path|
  source = File.read(path)
  next unless source.match?(%r{<nav(?:\s[^>]*)?>.*?</nav>}m) || source.match?(%r{<header\s+class="site-header".*?</header>}m)

  revised = source.sub(%r{<header\s+class="site-header".*?</header>}m, NAVIGATION)
  revised = revised.sub(%r{<nav(?:\s[^>]*)?>.*?</nav>}m, NAVIGATION) if revised == source

  unless revised.include?('href="/navigation.css"')
    revised = revised.sub('</head>', "  <link rel=\"stylesheet\" href=\"/navigation.css\">\n</head>")
  end
  unless revised.include?('src="/navigation.js"')
    revised = revised.sub('</head>', "  <script src=\"/navigation.js\" defer></script>\n</head>")
  end

  next if revised == source
  File.write(path, revised)
  updated += 1
end

puts "Synchronized navigation in #{updated} pages."
