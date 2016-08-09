import Ember from "ember";

export default Ember.Mixin.create({
  actions: {
    setTime23Hours() {
      Ember.$('#id_end_time').val('23:00');
    },

    setTime02Hours() {
      var start = Ember.$('#id_start_date');
      var end_date = Ember.$('#id_end_date');
      var end_time = Ember.$('#id_end_time');

      if (start.val() != '' && start.val() == end_date.val()) {
        var new_date = new Date(end_date.val());
        new_date.setDate(new_date.getDate() + 1);
        end_date.val(new_date.getISOString());
      }

      end_time.val('02:00');
    },
  }
});
