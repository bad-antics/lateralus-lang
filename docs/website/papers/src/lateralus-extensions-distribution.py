#!/usr/bin/env python3
"""Render 'Lateralus Extensions: Distribution & Verification' in the canonical Lateralus style."""
from pathlib import Path
from _lateralus_template import render_paper

OUT = Path(__file__).resolve().parents[1] / "pdf" / "lateralus-extensions-distribution.pdf"

render_paper(
    out_path=str(OUT),
    title="Lateralus Extensions",
    subtitle="Distribution & Publisher-Domain Verification",
    meta="bad-antics &middot; April 2026 &middot; Lateralus Tooling",
    abstract=(
        "This note documents how the three Lateralus VS Code extensions &mdash; <b>GrugBot420</b>, "
        "<b>Antikythera Digital</b>, and the <b>Lateralus Language</b> pack &mdash; are packaged, "
        "dual-published to the Visual Studio Marketplace and Open VSX, and how the "
        "<code>lateralus.dev</code> publisher domain is verified end-to-end. We cover the "
        "<code>vsce</code> and <code>ovsx</code> tool flows, Personal Access Token (PAT) "
        "scope pitfalls (the <code>TF400813</code> trap), the Open VSX namespace claim process, "
        "the Marketplace TXT-record verification for an apex-served Cloudflare zone, and the "
        "R2 + Pages hosting topology for direct VSIX downloads. The goal is reproducibility: "
        "any maintainer should be able to ship a signed, domain-verified extension from a clean "
        "checkout in under thirty minutes."
    ),
    sections=[
        ("1. What Shipped", [
            "Three extensions are now live across all three distribution channels (Marketplace, "
            "Open VSX, and direct download from <code>lateralus.dev</code>):",
            ("code",
             "grug-group420.grugbot420            v1.1.0   17.4 KB\n"
             "grug-group420.antikythera-digital   v0.2.0   42.1 KB\n"
             "grug-group420.lateralus-language    v0.3.0   58.7 KB"),
            "All three are signed with the same publisher identity and ship under matching MD5s "
            "across every mirror; the manifests advertise <code>lateralus.dev</code> as the "
            "verified publisher domain.",
        ]),
        ("2. Dual-Publishing Flow", [
            "Both registries accept the same VSIX artifact, so the build is a single "
            "<code>vsce package</code> invocation followed by two uploads:",
            ("code",
             "# build once\n"
             "npx vsce package --no-dependencies\n"
             "\n"
             "# publish to Visual Studio Marketplace\n"
             "npx vsce publish --packagePath grugbot420-1.1.0.vsix \\\n"
             "    --pat \"$VSCE_PAT\"\n"
             "\n"
             "# publish to Open VSX\n"
             "npx ovsx publish grugbot420-1.1.0.vsix \\\n"
             "    --pat \"$OVSX_PAT\""),
            ("h3", "2.1 The TF400813 PAT Trap"),
            "The Marketplace publish step initially failed with "
            "<code>TF400813: The user is not authorized to access this resource</code>. The "
            "fix is non-obvious: the PAT must be scoped to <b>Marketplace &rarr; Manage</b> "
            "<i>and</i> the &quot;Organization&quot; selector must be set to <b>All accessible "
            "organizations</b>. A token scoped to a single Azure DevOps org cannot publish, even "
            "if the publisher account itself has no AzDO org affiliation. Regenerating the PAT "
            "with the correct scope resolved it on the first retry.",
        ]),
        ("3. Open VSX Namespace Claim", [
            "Open VSX namespaces are first-come-first-served but require a verified claim before "
            "extensions show the &quot;verified&quot; badge. The claim is a GitHub issue against "
            "<code>EclipseFdn/open-vsx.org</code> using the <i>Publisher Agreement &amp; Namespace "
            "Claim</i> template. Our request is tracked as issue <b>#9925</b> for the "
            "<code>lateralus</code> namespace, filed under the <code>grug-group420</code> "
            "organization on Open VSX.",
            "Until the claim resolves, extensions still publish and install normally; only the "
            "verified badge is gated on the claim landing.",
        ]),
        ("4. Verifying the Publisher Domain", [
            "The Marketplace verifies a publisher domain by issuing a UUID and asking the "
            "publisher to expose it as a TXT record at a well-known label:",
            ("code",
             "_visual-studio-marketplace-<publisher>.<domain>   IN TXT  \"<UUID>\"\n"
             "\n"
             "# our concrete record:\n"
             "_visual-studio-marketplace-lateralus.lateralus.dev IN TXT \\\n"
             "    \"1b17ce53-8f77-4155-9e4e-8f779ac79620\""),
            ("h3", "4.1 Cloudflare Apex Gotcha"),
            "Because <code>lateralus.dev</code> is served from Cloudflare Pages on the apex, "
            "naively adding the TXT through the dashboard sometimes hides it under a "
            "&quot;proxied&quot; toggle that does not apply to TXT records. The reliable path "
            "is to add it via the API or the dashboard&apos;s <i>DNS &rarr; Records</i> view "
            "with type <code>TXT</code> explicitly &mdash; not via the <i>Custom hostnames</i> "
            "panel. Verification was confirmed live via DNS-over-HTTPS before clicking "
            "&quot;Verify&quot; in the Marketplace publisher portal.",
        ]),
        ("5. Hosting the Direct Downloads", [
            "Direct VSIX downloads live at <code>downloads.lateralus.dev</code>, which is bound "
            "to a Cloudflare R2 bucket (<code>lateralus-downloads</code>). Bucket listing is "
            "disabled, so the bucket cannot be enumerated; only known object paths resolve.",
            ("code",
             "https://downloads.lateralus.dev/extensions/grugbot420-1.1.0.vsix\n"
             "https://downloads.lateralus.dev/extensions/antikythera-digital-0.2.0.vsix\n"
             "https://downloads.lateralus.dev/extensions/lateralus-language-0.3.0.vsix"),
            "The <code>/extensions/</code> page on <code>lateralus.dev</code> is a Pages-served "
            "HTML index that links the three artifacts and surfaces their MD5s. The Pages site "
            "itself deploys via <code>wrangler pages deploy</code> using a Pages-scoped CF token; "
            "no Git connector is configured (the project is direct-upload).",
        ]),
        ("6. Security Posture", [
            "The site ships A+ security headers via Pages <code>_headers</code>:",
            ("code",
             "Content-Security-Policy:  default-src 'self'; ...\n"
             "Strict-Transport-Security: max-age=63072000; includeSubDomains; preload\n"
             "X-Content-Type-Options:    nosniff\n"
             "Referrer-Policy:           strict-origin-when-cross-origin\n"
             "Permissions-Policy:        accelerometer=(), camera=(), microphone=()"),
            "TLS is terminated by Google Trust Services WE1 (valid through 2026-07-04). MD5 "
            "checksums for every VSIX are published alongside the download links and match the "
            "Marketplace/Open VSX bytes verbatim, so a user who installs from any of the three "
            "channels gets the identical artifact.",
        ]),
        ("7. What's Next", [
            "Short term: land the Open VSX namespace verification (#9925) and add a "
            "<code>publisher</code> verification link from the extension manifests back to "
            "<code>lateralus.dev/extensions/</code>.",
            "Medium term: automate the dual-publish flow from a tagged release on the "
            "<code>bad-antics/lateralus-lang</code> repository, with reproducible builds keyed "
            "off the commit SHA so the MD5 in the release notes is verifiable from source.",
            "Long term: a Lateralus-native package format (<code>.ltlpkg</code>) that the OS "
            "package manager and the editor extensions both consume, eliminating the divergence "
            "between &quot;tooling I install in VS Code&quot; and &quot;tooling I install on "
            "Lateralus OS&quot;.",
        ]),
    ],
)
