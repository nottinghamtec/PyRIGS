'use strict';

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

function sass() {
  return gulp.src(["RIGS/scss/**/*.scss",
                    "node_modules/fullcalendar/dist/fullcalendar.css",
                    'node_modules/ajax-bootstrap-select/dist/css/ajax-bootstrap-select.min.css',
                    'node_modules/autocompleter/autocompleter.min.css',
                    'node_modules/@activix/bootstrap-datetimepicker/css/bootstrap-datetimepicker.min.css'])
    .pipe(sourcemaps.init())
    .pipe(flatten())
    .pipe(sass().on('error', sass.logError))
    .pipe(cleanCSS({compatibility: 'ie8'}))
    .pipe(postcss([ autoprefixer() ]))
    .pipe(sourcemaps.write())
    .pipe(gulp.dest('RIGS/static/css'))
    .pipe(browsersync.stream());
}

function scripts() {
    return gulp.src(['RIGS/static/js/src/**/.js',
                    'node_modules/jquery/dist/jquery.js',
                    'node_modules/ravenjs/ravenjs.js', //TODO Upgrade to Sentry
                    /* Bootstrap Plugins */
                    'node_modules/bootstrap/js/dist/dropdown.js',
                    'node_modules/bootstrap/js/dist/collapse.js',
                    'node_modules/bootstrap/js/dist/modal.js',
                    'node_modules/@fortawesome/fontawesome-free/js/all.js',
                    'node_modules/popper.js/**/popper.js',
                    'node_modules/moment/min/moment.min.js',
                    'node_modules/fullcalendar/dist/fullcalendar.js',
                    'node_modules/ajax-bootstrap-select/dist/js/ajax-bootstrap-select.min.js',
                    'node_modules/konami/konami.js',
                    'node_modules/autocompleter/autocompleter.min.js',
                    'node_modules/@activix/bootstrap-datetimepicker/js/bootstrap-datetimepicker.min.js'])
    .pipe(flatten())
    .pipe(terser())
    .pipe(gulp.dest('RIGS/static/js'))
    .pipe(browsersync.stream());
}

function browserSync(done) {
  exec('python manage.py runserver');
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
  gulp.watch("RIGS/static/scss/**/*", sass);
  gulp.watch("RIGS/static/js/**/*", scripts);
  gulp.watch(['templates/**/*.html', 'RIGS/templates/**/*.html', 'assets/templates/**/*.html', /*TODO'RIGS/.py'*/],  browserSyncReload);
}

exports.watch = gulp.parallel(watchFiles, browserSync);
