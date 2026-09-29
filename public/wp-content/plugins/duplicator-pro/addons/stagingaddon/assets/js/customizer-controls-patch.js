/**
 * Duplicator Staging Customizer — controls-page patch
 *
 * WordPress core's customize-controls.js rejects any URL whose pathname
 * matches /\/wp-(admin|includes|content)(\/|$)/ inside the previewUrl
 * setter. Staging sites live under /wp-content/duplicator-backups/dup_staging/,
 * so the initial URL is rejected and the preview iframe never loads.
 *
 * This script wraps the setter. URLs under the staging baseUrl pass through
 * unchanged; everything else delegates to core's original setter so the
 * security intent of the regex is preserved.
 *
 * Upstream fix tracked at https://core.trac.wordpress.org/ticket/65030.
 */
(function () {
    'use strict';

    if (!window.wp || !wp.customize || typeof wp.customize.bind !== 'function') {
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

    // wp.customize.previewer is created inside core's DOMContentLoaded
    // handler, after this footer script runs. Defer install until the
    // Customizer 'ready' event fires so the previewer instance exists.
    wp.customize.bind('ready', function () {
        if (
            !wp.customize.previewer
            || !wp.customize.previewer.previewUrl
            || typeof wp.customize.previewer.previewUrl.setter !== 'function'
            || typeof wp.customize.previewer.previewUrl._setter !== 'function'
        ) {
            return;
        }

        try {
            var previewUrl     = wp.customize.previewer.previewUrl;
            var originalSetter = previewUrl._setter;

            previewUrl.setter(function (to) {
                try {
                    if (matchesStagingBase(to)) {
                        return to;
                    }
                } catch (e) {
                    // fall through to core's setter
                }
                return originalSetter.call(this, to);
            });

            // Core's original setter already rejected the initial URL before
            // our wrapper was installed — previewUrl.get() returns null and
            // the iframe src stays empty. Re-set from the raw preview URL
            // in wp.customize.settings to kick the iframe to life.
            if (
                previewUrl.get() === null
                && wp.customize.settings
                && wp.customize.settings.url
                && wp.customize.settings.url.preview
            ) {
                previewUrl.set(wp.customize.settings.url.preview);
            }
        } catch (e) {
            if (window.console && typeof console.warn === 'function') {
                console.warn(
                    'Duplicator staging Customizer controls patch: install failed, falling back to core behavior',
                    e
                );
            }
        }
    });
}());
