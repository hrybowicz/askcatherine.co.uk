/**
 * Staging Addon Scripts
 */

(function($) {
    'use strict';

    window.DupliJs = window.DupliJs || {};

    /**
     * Staging page controller
     */
    DupliJs.Staging = {
        // Config values set via wp_localize_script
        nonce: '',
        deleteNonce: '',
        validateNonce: '',
        dlgDeleteMessageId: '',
        i18n: {},

        // Internal state
        modalBox: null,
        modalContent: null,
        checkNonce: '',
        pendingStagingIds: [],
        statusPollInterval: null,

        /**
         * Initialize the staging controller
         *
         * @param {Object} config Configuration from wp_localize_script
         */
        init: function(config) {
            this.nonce = config.nonce || '';
            this.deleteNonce = config.deleteNonce || '';
            this.validateNonce = config.validateNonce || '';
            this.dlgDeleteMessageId = config.dlgDeleteMessageId || '';
            this.i18n = config.i18n || {};

            this.checkNonce = config.checkNonce || '';
            this.pendingStagingIds = config.pendingStagingIds || [];

            this.modalBox = new DuplicatorModalBox();
            this.bindEvents();
            this.startStatusPolling();

            // Auto-trigger delete if requested (with delay to ensure tickbox is ready)
            if (config.autoDeleteStagingId) {
                var self = this;
                setTimeout(function() {
                    self.deleteSingle(config.autoDeleteStagingId);
                }, 100);
            }
        },

        /**
         * Bind page events
         */
        bindEvents: function() {
            var self = this;

            // Open modal buttons
            $('#dupli-staging-create-new-btn, .dupli-staging-open-modal-btn').on('click', function() {
                self.openCreateModal();
            });
        },

        /**
         * Open the create staging modal
         */
        openCreateModal: function() {
            var self = this;
            var content = $('#dupli-staging-create-modal-content').html();
            this.modalBox.setOptions({
                htmlContent: content,
                closeInContent: true,
                closeColor: '#666',
                openCallback: function(modalContent) {
                    self.modalContent = $(modalContent);
                    self.bindModalEvents();
                }
            });
            this.modalBox.open();
        },

        /**
         * Bind modal events
         */
        bindModalEvents: function() {
            var self = this;
            var $modal = this.modalContent;

            // Backup selection change - clear any previous validation errors
            $modal.find('select[name="backup_id"]').on('change', function() {
                $modal.find('.dupli-staging-validation-result').hide().empty();
            });

            // Cancel button in modal
            $modal.find('#dupli-staging-cancel-btn').on('click', function() {
                self.closeModal();
            });

            // Create form submit - validate first, then create if valid
            $modal.find('#dupli-staging-create-form').on('submit', function(e) {
                e.preventDefault();
                self.validateAndCreate();
            });
        },

        /**
         * Close the modal
         */
        closeModal: function() {
            if (this.modalBox) {
                this.modalBox.close();
            }
            this.modalContent = null;
        },

        /**
         * Toggle all checkboxes for bulk delete
         */
        SetDeleteAll: function() {
            var state = $('input#dup-chk-all').is(':checked') ? 1 : 0;
            $("input[name=delete_confirm]").each(function() {
                this.checked = (state) ? true : false;
            });
        },

        /**
         * Get list of selected staging site IDs
         *
         * @returns {Array} Array of selected IDs
         */
        GetDeleteList: function() {
            var arr = [];
            $("input[name=delete_confirm]:checked").each(function() {
                arr.push(this.id);
            });
            return arr;
        },

        /**
         * Delete a single staging site
         *
         * @param {number} id Staging site ID
         */
        deleteSingle: function(id) {
            // Select the checkbox for this item
            $('#' + id).prop('checked', true);
            // Set dropdown to delete
            $('#dupli-staging-bulk-actions').val('delete');
            // Show confirmation
            this.ConfirmDelete();
        },

        /**
         * Execute deletion of selected staging sites
         */
        Delete: function() {
            var self = this;
            var stagingIds = this.GetDeleteList();

            DupliJs.Util.ajaxWrapper(
                {
                    action: 'duplicator_staging_delete',
                    staging_ids: stagingIds,
                    nonce: this.deleteNonce
                },
                function(result, data, funcData, textStatus, jqXHR) {
                    window.location.reload();
                    return '';
                },
                function(result, data, funcData, textStatus, jqXHR) {
                    DupliJs.addAdminMessage(data.message || self.i18n.errorDeleting, 'error');
                    return '';
                }
            );
        },

        /**
         * Validate backup and create staging site
         */
        validateAndCreate: function() {
            var self = this;
            var $modal = this.modalContent;

            if (!$modal) {
                DupliJs.addAdminMessage(this.i18n.modalNotFound, 'error');
                return;
            }

            var backupId = $modal.find('select[name="backup_id"]').val();
            var title = $modal.find('input[name="title"]').val();

            if (!backupId) {
                DupliJs.addAdminMessage(this.i18n.selectBackupFirst, 'error');
                return;
            }

            var $createBtn = $modal.find('#dupli-staging-create-btn');
            $createBtn.prop('disabled', true);
            $createBtn.find('i').removeClass('fa-plus-circle').addClass('fa-spinner fa-spin');
            $modal.find('.dupli-staging-validation-result').hide().empty();

            // First validate the backup
            DupliJs.Util.ajaxWrapper(
                {
                    action: 'duplicator_staging_validate',
                    nonce: self.validateNonce,
                    backup_id: backupId
                },
                function(result, data, funcData) {
                    if (funcData.valid) {
                        // Validation passed - proceed with creation
                        self.createStaging(backupId, title);
                    } else {
                        // Validation failed - close modal and show error
                        self.closeModal();

                        var issues = funcData.issues || [self.i18n.unknownValidationError];
                        var issuesHtml = '<p>' + self.i18n.cannotCreateStaging + '</p><ul>';
                        for (var i = 0; i < issues.length; i++) {
                            var escapedIssue = $('<div/>').text(issues[i]).html();
                            issuesHtml += '<li>' + escapedIssue + '</li>';
                        }
                        issuesHtml += '</ul>';

                        DupliJs.addAdminMessage(issuesHtml, 'error');
                    }
                },
                function() {
                    self.closeModal();
                    return self.i18n.validationRequestFailed;
                }
            );
        },

        /**
         * Start polling for pending staging sites status changes
         */
        startStatusPolling: function() {
            if (this.pendingStagingIds.length === 0) {
                return;
            }

            var self = this;
            this.statusPollInterval = setInterval(function() {
                self.checkPendingStatus();
            }, 5000);
        },

        /**
         * Check status of pending staging sites and reload page when any completes
         */
        checkPendingStatus: function() {
            var self = this;
            var stagingId = this.pendingStagingIds[0];

            DupliJs.Util.ajaxWrapper(
                {
                    action: 'duplicator_staging_check_complete',
                    nonce: self.checkNonce,
                    staging_id: stagingId
                },
                function(result, data, funcData) {
                    if (funcData.complete || funcData.notFound) {
                        clearInterval(self.statusPollInterval);
                        window.location.reload();
                    }
                },
                null,
                {showProgress: false, silentSuccess: true, silentError: true}
            );
        },

        /**
         * Create staging site
         *
         * @param {number} backupId Backup package ID
         * @param {string} title Staging site title
         */
        createStaging: function(backupId, title) {
            var self = this;
            var $modal = this.modalContent;
            var colorScheme = $modal ? $modal.find('select[name="color_scheme"]').val() : 'sunrise';

            DupliJs.Util.ajaxWrapper(
                {
                    action: 'duplicator_staging_create',
                    nonce: self.nonce,
                    backup_id: backupId,
                    title: title,
                    color_scheme: colorScheme
                },
                function(result, data, funcData) {
                    if (funcData.stagingId) {
                        if (funcData.installerPageUrl) {
                            window.open(funcData.installerPageUrl, '_blank');
                        }
                        self.closeModal();
                        window.location.reload();
                    } else {
                        self.closeModal();
                        return self.i18n.failedToCreate + ' ' + (data.message || self.i18n.unknownError);
                    }
                },
                function() {
                    self.closeModal();
                    return self.i18n.stagingRequestFailed;
                }
            );
        }
    };

})(jQuery);
