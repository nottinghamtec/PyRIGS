'use strict';

var gulp = require('gulp');

var sourcemaps = require('gulp-sourcemaps');

var sass = require('gulp-sass');
var concat = require('gulp-concat');

var batch = require('gulp-batch');
var watch = require('gulp-watch');

var APPS = [
    'RIGS'
];

var SASS_INCLUDE_PATHS = APPS.map(function (elem) {
    return './' + elem + '/static/scss'
}).concat(['./node_modules']);

function css(opts) {
    return gulp.src('PyRIGS/static/scss/screen.scss')
        .pipe(sourcemaps.init())
        .pipe(sass(
            {includePaths: SASS_INCLUDE_PATHS}
        )).on('error', sass.logError)
        .pipe(sourcemaps.write('.'))
        .pipe(gulp.dest('dist/css'));
}

gulp.task('css', function () {
    return css()
});

gulp.task('watch', function () {
    batch(function (events, done) {
        gulp.start('css', done);
    });
    watch(SASS_INCLUDE_PATHS.concat(['PyRIGS/static/scss/screen.scss']), batch(function (events, done) {
        gulp.start('css', done);
    }));
});

// JS

var JS_LIBS = [
    './node_modules/jquery/dist/jquery.js',
    './node_modules/tether/dist/js/tether.js',
    './node_modules/bootstrap/dist/js/bootstrap.js'
];

function js_lib() {
    return gulp.src(JS_LIBS)
        .pipe(sourcemaps.init())
        .pipe(concat('lib.js'))
        .pipe(sourcemaps.write('.'))
        .pipe(gulp.dest('dist/js'));
}

gulp.task('js_lib', function () {
    return js_lib()
});

// Frontend tasks
gulp.task('frontend', [
    'css',
    'js_lib'
]);
