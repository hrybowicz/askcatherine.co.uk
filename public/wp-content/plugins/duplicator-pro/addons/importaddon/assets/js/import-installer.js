/*! dup import installer */
(function ($) {
    DupliImportInstaller = {
        installerIframe: $('#dupli-import-installer-iframe'),
        init: function () {
            DupliImportInstaller.installerIframe.on("load", function () {
                DupliImportInstaller.installerIframe.contents()
                    .find('#page-step1')
                    .on('click', '> .ui-dialog #db-install-dialog-confirm-button', function () {
                        $('#dupli-import-installer-modal').removeClass('no-display');
                    });
            });
        },
        resizeIframe: function () {
            let height = DupliImportInstaller.installerIframe.contents()
                .find('html').css('overflow', 'hidden')
                .outerHeight(true);
            console.log('height', height);
            DupliImportInstaller.installerIframe.css({
                'height': height + 'px'
            })
        }
    }

    DupliImportInstaller.init();
    DuplicatorTooltip.load();

})(jQuery);