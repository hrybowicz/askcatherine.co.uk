/**
 * Duplicator Staging Customizer — preview-iframe patch
 *
 * WordPress core's customize-preview.js::api.isLinkPreviewable rejects any
 * link whose pathname matches /\/wp-(admin|includes|content)(\/|$)/. Staging
 * sites live under /wp-content/duplicator-backups/dup_staging/, so every
 * internal link in the preview is marked unpreviewable (cursor: not-allowed)
 * and clicks are suppressed.
 *
 * This script wraps isLinkPreviewable. Links under the staging baseUrl
 * return true; everything else delegates to core so the security intent
 * is preserved.
 *
 * Upstream fix tracked at https://core.trac.wordpress.org/ticket/65030.
 */
(function () {
    'use strict';

    if (
        !window.wp
        || !wp.customize
        || typeof wp.customize.isLinkPreviewable !== 'function'
    ) {
        return;
    }

    if (!window.dupli_staging_customizer || !dupli_staging_customizer.baseUrl) {
        return;
    }

    var EXCLUDED_PATHS = ['/wp-login.php', '/wp-signup.php', '/wp-admin/admin-ajax.php'];

    function matchesStagingBase(urlStr) {
        var parsed, parsedBase;
        try {
            parsed     = new URL(urlStr, window.location.href);
            parsedBase = new URL(dupli_staging_customizer.baseUrl);
        } catch (e) {
            return false;
        }

        if (parsed.origin !== parsedBase.origin) {
            return false;
        }

        // Path-prefix match with segment boundary. The trailing slash on baseUrl
        // is stripped for comparison so a home-URL-style href without a trailing
        // slash still matches, while prefix collisions like "/staging/" vs
        // "/staging-other/" are blocked by requiring a "/" right after the base.
        var baseNoSlash = parsedBase.pathname.replace(/\/$/, '');
        var urlPath     = parsed.pathname;
        if (urlPath !== baseNoSlash && urlPath.indexOf(baseNoSlash + '/') !== 0) {
            return false;
        }

        for (var i = 0; i < EXCLUDED_PATHS.length; i++) {
            if (parsed.pathname.indexOf(EXCLUDED_PATHS[i]) !== -1) {
                return false;
            }
        }

        return true;
    }

    try {
        var originalIsLinkPreviewable = wp.customize.isLinkPreviewable;

        wp.customize.isLinkPreviewable = function (element, options) {
            try {
                if (element && element.href && matchesStagingBase(element.href)) {
                    return true;
                }
            } catch (e) {
                // fall through to core
            }
            return originalIsLinkPreviewable.call(this, element, options);
        };
    } catch (e) {
        if (window.console && typeof console.warn === 'function') {
            console.warn(
                'Duplicator staging Customizer preview patch: install failed, falling back to core behavior',
                e
            );
        }
    }
}());
