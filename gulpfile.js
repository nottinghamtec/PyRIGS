"use strict";

var gulp = require('gulp');

var concat = require('gulp-concat');
var rename = require('gulp-rename');
var terser = require('gulp-terser');
var sass = require('gulp-sass');
var flatten = require('gulp-flatten');
var cleanCSS = require('gulp-clean-css');
var autoprefixer = require('autoprefixer')
var postcss = require('gulp-postcss')
var sourcemaps = require('gulp-sourcemaps');
var browsersync = require('browser-sync').create();
var { exec } = require("child_process");

sass.compiler = require('node-sass');

function styles(done) {
    return gulp.src(['RIGS/static/scss/**/*.scss',
                    'node_modules/fullcalendar/dist/fullcalendar.css',
                    'node_modules/ajax-bootstrap-select/dist/css/ajax-bootstrap-select.min.css',
                    'node_modules/autocompleter/autocomplete.css',
                    'node_modules/@activix/bootstrap-datetimepicker/css/bootstrap-datetimepicker.min.css'])
    .pipe(sourcemaps.init())
    .pipe(sass().on('error', sass.logError))
    .pipe(postcss([ autoprefixer() ]))
    .pipe(sourcemaps.write())
    .pipe(gulp.dest('RIGS/static/css'))
    .pipe(browsersync.stream());
}

function scripts() {
    return gulp.src(['RIGS/static/js/src/**/.js',
                    'node_modules/jquery/dist/jquery.js',
                    'node_modules/popper.js/dist/umd/popper.js',
                    'node_modules/ravenjs/ravenjs.js', //TODO Upgrade to Sentry
                    /* Bootstrap Plugins */
                    'node_modules/bootstrap/js/dist/util.js',
                    'node_modules/bootstrap/js/dist/tooltip.js',
                    'node_modules/bootstrap/js/dist/popover.js',
                    'node_modules/bootstrap/js/dist/dropdown.js',
                    'node_modules/bootstrap/js/dist/collapse.js',
                    'node_modules/bootstrap/js/dist/modal.js',
                    'node_modules/bootstrap/js/dist/alert.js',

                    'node_modules/@fortawesome/fontawesome-free/js/all.js',
                    'node_modules/moment/moment.js',
                    'node_modules/fullcalendar/dist/fullcalendar.js',
                    'node_modules/ajax-bootstrap-select/dist/js/ajax-bootstrap-select.js',
                    'node_modules/konami/konami.js',
                    'node_modules/autocompleter/autocomplete.js',
                    'node_modules/@activix/bootstrap-datetimepicker/js/bootstrap-datetimepicker.js'])
    .pipe(flatten())
    .pipe(terser())
    .pipe(gulp.dest('RIGS/static/js'))
    .pipe(browsersync.stream());
}

function browserSync(done) {
  exec('python manage.py runserver');
  // TODO Pipe errors from django to gulp output
  // TODO Wait for Django server to come up before browsersync, it seems inconsistent
  browsersync.init({
    notify: true,
    port: 8001,
    proxy: 'localhost:8000'
  });
  done();
}

function browserSyncReload(done) {
  browsersync.reload();
  done();
}

function watchFiles() {
  gulp.watch("RIGS/static/scss/**/*", styles);
  gulp.watch("RIGS/static/js/**/*", scripts);
  gulp.watch(['templates/**/*.html', 'RIGS/templates/**/*.html', 'assets/templates/**/*.html'],  browserSyncReload);
}

exports.css = styles;
exports.js = scripts;
exports.watch = gulp.parallel(watchFiles, browserSync);
