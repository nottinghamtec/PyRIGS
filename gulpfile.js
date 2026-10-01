"use strict";

var gulp = require('gulp');

const terser = require('gulp-uglify');
const sass = require('gulp-sass')(require('sass'));
const flatten = require('gulp-flatten');
const autoprefixer = require('autoprefixer')
const postcss = require('gulp-postcss')
const sourcemaps = require('gulp-sourcemaps');
const browsersync = require('browser-sync').create();
const { exec } = require("child_process");
const spawn = require('child_process').spawn;
const cssnano = require('cssnano');
const con = require('gulp-concat');
const gulpif = require('gulp-if');

function fonts(done) {
    return gulp.src('node_modules/@fortawesome/fontawesome-free/webfonts/fa-solid-900.*', { encoding: false })
        .pipe(gulp.dest('pipeline/built_assets/fonts'))
        .pipe(browsersync.stream());
}

function styles(done) {
    const bs_select = ["tom-select.bootstrap5.css"]
    return gulp.src(['pipeline/source_assets/scss/**/*.scss',
                    'node_modules/fullcalendar/main.css',
                    'node_modules/tom-select/dist/css/tom-select.bootstrap5.css',
                    'node_modules/easymde/dist/easymde.min.css'
                    ])
    .pipe(sourcemaps.init())
    // Bootstrap 4's SCSS can only be consumed via @import (its partials share global variables),
    // so that one deprecation stays silenced until we move to a Sass-module-aware framework.
    // quietDeps hides the remaining deprecations raised inside third-party stylesheets.
    .pipe(sass({
        loadPaths: ['.'],
        quietDeps: true,
        silenceDeprecations: ['import'],
    }).on('error', sass.logError))
    .pipe(gulpif(function(file) { return bs_select.includes(file.relative);}, con('selects.css')))
    .pipe(postcss([ autoprefixer(), cssnano() ]))
    .pipe(sourcemaps.write())
    .pipe(gulp.dest('pipeline/built_assets/css'))
    .pipe(browsersync.stream());
}

function scripts() {
    const dest = 'pipeline/built_assets/js';
    const base_scripts = ["src.js", "konami.js"];
    const bs_select = ["tom-select.complete.js"]
    const interaction = ["html5sortable.min.js", "interaction.js"]
    return gulp.src([/* Bootstrap bundle includes Popper */
                    'node_modules/bootstrap/dist/js/bootstrap.bundle.js',

                    'node_modules/html5sortable/dist/html5sortable.min.js',
                    'node_modules/clipboard/dist/clipboard.min.js',
                    'node_modules/moment/moment.js',
                    'node_modules/fullcalendar/main.js',
                    'node_modules/tom-select/dist/js/tom-select.complete.js',
                    'node_modules/easymde/dist/easymde.min.js',
                    'node_modules/konami/konami.js',
                    'pipeline/source_assets/js/**/*.js',])
    .pipe(gulpif(function(file) { return base_scripts.includes(file.relative);}, con('base.js')))
    .pipe(gulpif(function(file) { return bs_select.includes(file.relative);}, con('selects.js')))
    .pipe(gulpif(function(file) { return interaction.includes(file.relative);}, con('interaction.js')))
    .pipe(gulpif(function(file) { return file.relative === "bootstrap.bundle.js";}, con('jpop.js')))
    .pipe(flatten())
    // Only minify if filename does not already denote it as minified
    .pipe(gulpif(function(file) { return file.path.indexOf("min") === -1;},terser()))
    .pipe(gulp.dest(dest))
    .pipe(browsersync.stream());
}

function browserSync(done) {
  spawn('python', ['manage.py', 'runserver'], {stdio: 'inherit'});
  browsersync.init({
    notify: true,
    open: false,
    port: 8001,
    proxy: '127.0.0.1:8000'
  });
  done();
}

function browserSyncReload(done) {
  browsersync.reload();
  done();
}

function watchFiles() {
  gulp.watch("pipeline/source_assets/scss/**/*.scss", styles);
  gulp.watch("pipeline/source_assets/js/**/*.js", scripts);
  gulp.watch("**/templates/*.html", browserSyncReload);
}

exports.build = gulp.parallel(styles, scripts, fonts);
exports.watch = gulp.parallel(watchFiles, browserSync);
