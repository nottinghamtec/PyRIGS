import Ember from "ember";
import config from "./config/environment";

const Router = Ember.Router.extend({
  location: config.locationType,
  rootURL: config.rootURL
});

Router.map(function () {
  this.route('event', function () {
    this.route('create');
    this.route('show', {
      path: ':id'
    });
    this.route('duplicate', {
      path: ':id/duplicate'
    });
    this.route('edit', {
      path: ':id/edit'
    });
  });

  this.route('legacy', {path: '/*wildcard'});
});

export default Router;
