import Ember from "ember";
import SetTimeMixinMixin from "pyrigs/mixins/set-time-mixin";
import {module, test} from "qunit";

module('Unit | Mixin | set time mixin');

// Replace this with your real tests.
test('it works', function (assert) {
  let SetTimeMixinObject = Ember.Object.extend(SetTimeMixinMixin);
  let subject = SetTimeMixinObject.create();
  assert.ok(subject);
});
