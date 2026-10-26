# Orbit search visibility

Public search landing: https://crypto-portfolio-tracker-rouge.vercel.app/
Private workspace: https://crypto-portfolio-tracker-rouge.vercel.app/app.html
Sitemap: https://crypto-portfolio-tracker-rouge.vercel.app/sitemap.xml

## Implemented

Four static public pages: product overview, original weighted-average P&L worked example, wallet tracking guide, and transparent product/data limitations. No login or JavaScript is required to read them. Each has a unique title, description, canonical URL, social metadata, one main heading, semantic navigation and internal links. Public CSS is small and responsive and uses system fonts. Only allowlisted public files enter the CDN build. The root is the public homepage; the private workspace is now /app.html and is noindex. Existing account sessions continue using the same cookies and APIs. The old product URL and /index.html permanently redirect to the root. The sitemap contains only public content. API routes carry noindex headers on Vercel. Robots allows crawling so search engines can see noindex. Authentication remains the access-control boundary.

No fake reviews, ratings, investment results, public-signup claims or mass-produced coin pages. No software rich-result markup is claimed: Google requires a genuine rating/review and offer information for its software-app rich result, which this owner-restricted product cannot currently substantiate.

## Next owner steps

1. Verify this exact HTTPS URL-prefix property in Google Search Console. Use a verification method available in the owner account; no fabricated verification token is installed.
2. Submit /sitemap.xml and inspect the four public URLs. Request indexing once; requests do not guarantee indexing or rank.
3. Monitor indexing, impressions, relevant queries, clicks and Core Web Vitals; compare over several weeks. No ranking improvement is claimed before measurement.
4. Choose a stable branded custom domain if desired before promoting widely, then update canonical URLs, social URLs and sitemap together and permanently redirect the old public URLs. A domain purchase is not required for the current release and has not been made.
5. Publish useful product-specific examples and reviewed tutorials when features change. Add genuine authorship/review provenance only when established. Earn relevant links through real product discovery; avoid paid link schemes and keyword stuffing.
6. If public signup is enabled later, revisit conversion copy and product metadata. Current copy honestly states owner-restricted access.

## Research (Google primary guidance)

- SEO Starter Guide: https://developers.google.com/search/docs/fundamentals/seo-starter-guide
- Helpful content: https://developers.google.com/search/docs/fundamentals/creating-helpful-content
- noindex and crawlability: https://developers.google.com/search/docs/crawling-indexing/block-indexing
- Software app rich-result eligibility: https://developers.google.com/search/docs/appearance/structured-data/software-app
- Crawling/indexing requests: https://developers.google.com/search/docs/crawling-indexing/ask-google-to-recrawl

Rank is not guaranteed. Indexing can take days or weeks. Search Console access and verified field performance are still needed for an actual search-performance assessment.

## Second audit improvements

- Root-level public homepage, visible app entry point, and permanent duplicate-URL redirects. Canonicals, sitemap, navigation and social URLs consistently prefer the root.
- WebSite microdata on the root with visible brand Orbit and alternative name Orbit Crypto Portfolio. BreadcrumbList microdata on both guides. Microdata avoids changing the restrictive script CSP. Markup expresses a preference, not a promised search feature.
- Favicon and real product screenshot for social previews; no invented ratings or endorsements.
- Public pages use one small local stylesheet, system fonts and no application JavaScript or database requests. The app remains authenticated and noindex at /app.html.
- API and account data stay outside the sitemap. Unknown routes retain 404 responses.
- Tests verify canonical paths, redirect configuration, schema presence, internal links, app separation, static build allowlisting and the public CSS size budget.

Additional primary research:
- Site-name requirements: https://developers.google.com/search/docs/appearance/site-names
- Canonicalization and redirect signals: https://developers.google.com/search/docs/crawling-indexing/consolidate-duplicate-urls

No Search Console ownership or field Core Web Vitals data has been provided. These implementation checks are not a Lighthouse score, a rich-results validation, an indexing guarantee or measured ranking improvement.

## Supplied Lighthouse report follow-up

The user-provided download.pdf (39 pages, captured 26 October 2026) reports performance 61, accessibility 91, best practices 92 and SEO 100. It explicitly warns that browser extensions and IndexedDB affect this run. Page 11 identifies unnamed controls and positive tabindex in extension-injected chat UI; pages 3–8 attribute substantial JavaScript activity to extension URLs. Page 20 reports extension messaging errors. Those findings should not be treated as proof that Orbit ships the extension scripts or that all reported CPU time belongs to Orbit.

The actionable first-party rendering dependency is /public_site.css. Production public HTML now inlines this small stylesheet, eliminating its blocking request without JavaScript, remote fonts or weaker CSP. A visible keyboard focus style is included. The private application's styles and scripts remain unchanged.

SVG, multi-resolution ICO, 96px PNG and Apple touch icons are linked from public and private pages. Icons have explicit allowlisted static routes and MIME types. New scores have not been claimed; repeat Lighthouse in a clean browser profile with extensions disabled to compare.

## Public registration release

Public registration is explicitly enabled by ORBIT_PUBLIC_REGISTRATION=1 in production. Account creation links open /app.html#create-account. The build replaces the earlier owner-only product copy and sets the registration metadata to public. Authentication, per-account authorization, password minimums and rate limits remain active. Registration defaults remain restricted when an owner email is configured and the public flag is absent.
