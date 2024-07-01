"use strict";

var gulp = require('gulp');

const terser = require('gulp-uglify');
const sass = require('gulp-sass')(require('node-sass'));
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
    const bs_select = ["bootstrap-select.css", "ajax-bootstrap-select.css"]
    return gulp.src(['pipeline/source_assets/scss/**/*.scss',
                    'node_modules/fullcalendar/main.css',
                    'node_modules/bootstrap-select/dist/css/bootstrap-select.css',
                    'node_modules/ajax-bootstrap-select/dist/css/ajax-bootstrap-select.css',
                    'node_modules/easymde/dist/easymde.min.css'
                    ])
    .pipe(sourcemaps.init())
    .pipe(sass().on('error', sass.logError))
    .pipe(gulpif(function(file) { return bs_select.includes(file.relative);}, con('selects.css')))
    .pipe(postcss([ autoprefixer(), cssnano() ]))
    .pipe(sourcemaps.write())
    .pipe(gulp.dest('pipeline/built_assets/css'))
    .pipe(browsersync.stream());
}

function scripts() {
    const dest = 'pipeline/built_assets/js';
    const base_scripts = ["src.js", "util.js", "alert.js", "collapse.js", "dropdown.js", "modal.js", "konami.js"];
    const bs_select = ["bootstrap-select.js", "ajax-bootstrap-select.js"]
    const interaction = ["html5sortable.min.js", "interaction.js"]
    const jpop = ["jquery.min.js", "popper.min.js"]
    return gulp.src(['node_modules/jquery/dist/jquery.min.js',
                    /* JQuery Plugins */
                    'node_modules/popper.js/dist/umd/popper.min.js',
                    /* Bootstrap Plugins */
                    'node_modules/bootstrap/js/dist/util.js',
                    'node_modules/bootstrap/js/dist/tooltip.js',
                    'node_modules/bootstrap/js/dist/popover.js',
                    'node_modules/bootstrap/js/dist/dropdown.js',
                    'node_modules/bootstrap/js/dist/collapse.js',
                    'node_modules/bootstrap/js/dist/modal.js',
                    'node_modules/bootstrap/js/dist/alert.js',

                    'node_modules/html5sortable/dist/html5sortable.min.js',
                    'node_modules/clipboard/dist/clipboard.min.js',
                    'node_modules/moment/moment.js',
                    'node_modules/fullcalendar/main.js',
                    'node_modules/bootstrap-select/dist/js/bootstrap-select.js',
                    'node_modules/ajax-bootstrap-select/dist/js/ajax-bootstrap-select.js',
                    'node_modules/easymde/dist/easymde.min.js',
                    'node_modules/konami/konami.js',
                    'pipeline/source_assets/js/**/*.js',])
    .pipe(gulpif(function(file) { return base_scripts.includes(file.relative);}, con('base.js')))
    .pipe(gulpif(function(file) { return bs_select.includes(file.relative);}, con('selects.js')))
    .pipe(gulpif(function(file) { return interaction.includes(file.relative);}, con('interaction.js')))
    .pipe(gulpif(function(file) { return jpop.includes(file.relative);}, con('jpop.js')))
    .pipe(flatten())
    // Only minify if filename does not already denote it as minified
    .pipe(gulpif(function(file) { return file.path.indexOf("min") == -1;},terser()))
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
