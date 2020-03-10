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

sass.compiler = require('node-sass');

gulp.task('sass', function () {
  return gulp.src(['web_assets/scss/**/*.scss', 'node_modules/fullcalendar/dist/fullcalendar.css'])
    .pipe(sourcemaps.init())
    .pipe(flatten())
    .pipe(sass().on('error', sass.logError))
    .pipe(cleanCSS({compatibility: 'ie8'}))
    .pipe(postcss([ autoprefixer() ]))
    .pipe(sourcemaps.write())
    .pipe(gulp.dest('RIGS/static/css'));
});

gulp.task('scripts', function() {
    return gulp.src(['web_assets/js/**/*.js', 'node_modules/bootstrap/**/bootstrap.min.js', 'node_modules/popper\.js/**/popper.js', 'node_modules/moment/min/moment.min.js', 'node_modules/@fortawesome/fontawesome-free/js/all.js', 'node_modules/jquery/dist/jquery.js', 'node_modules/fullcalendar/dist/fullcalendar.js'])
    .pipe(flatten())
    .pipe(terser())
    .pipe(gulp.dest('RIGS/static/js'));
});

exports.default = gulp.parallel('sass', 'scripts');
exports.build = gulp.parallel('sass', 'scripts');
