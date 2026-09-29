const defaultConfig = require( '@wordpress/scripts/config/webpack.config' );

const defaultEntries = defaultConfig.entry();

module.exports = {
	...defaultConfig,
	// Needed for the 'lib-font' package to work.
	resolve: {
		fallback: {
			fs: false,
			zlib: false,
		},
		symlinks: false,
	},
	entry: {
		...defaultEntries,
		'block-elements': './src/block-elements.js',
		'font-library': './src/font-library.js',
		'site-library': './src/site-library.js',
		customizer: './src/customizer.js',
		dashboard: './src/dashboard.js',
		editor: './src/editor.js',
		packages: './src/packages.scss',
		'adjacent-posts': './src/adjacent-posts.js',
	},
	output: {
		...defaultConfig.output,
		path: __dirname + '/dist',
	},
};
