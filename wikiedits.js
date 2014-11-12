Edits = new Mongo.Collection("edits");
PieData = new Mongo.Collection("piedata")
BarData = new Mongo.Collection("bardata")

if (Meteor.isClient) {
  Meteor.startup(function() {
    Meteor.call('clearPie')
    Meteor.call('clearBar')
    Session.set("control_btn_text", "Pause");
    Session.set("control_btn_icon", "pause");
  });

  Meteor.subscribe('edits');
  Meteor.subscribe('piedata');
  Meteor.subscribe('bardata');


  Template.body.helpers({
    edits: function () {
      if (Session.get("control_btn_icon") == "pause") {
        return Edits.find({}, {sort: {createdAt: -1}});
      } else {
        return Session.get("edits_frozen");
      }
    }
  });


  Template.controls.helpers({
    icon: function () {
      return Session.get("control_btn_icon");
    },
    text: function () {
      return Session.get("control_btn_text");
    }
  });

    Template.body.events = {
    'click #about': function () {
        $('.modal').modal('show')
    }


  };



  Template.controls.events = {
    'click #control_btn': function () {
      //var new_player_name = document.getElementById("new_player_name").value;
      if (Session.get("control_btn_icon") == "pause") {
        Session.set("control_btn_text", "Continue");
        Session.set("control_btn_icon", "play")

        // Freeze values
        Session.set("edits_frozen", Edits.find({}, {sort: {createdAt: -1}}).fetch())
        Session.set("piechart_frozen", PieData.find({}).fetch())
        Session.set("barchart_frozen", BarData.find({}).fetch())

        //enable summary popups
        $('.apopup').popup();
      } else {
        Session.set("control_btn_text", "Pause");
        Session.set("control_btn_icon", "pause");

        //Remove popups
        $('.apopup').popup('destroy');
      }
    },
    'click #reset': function () {
      //var new_player_name = document.getElementById("new_player_name").value;
      Meteor.call('clearPie')
      Meteor.call('clearBar')
    }


  };

  Template.piechart.rendered = function () {
   this.autorun(function (computation) {
        //dependency to make code autorun when data changes
        Template.currentData();

        if (Session.get("control_btn_icon") == "pause") {
          freqs = PieData.find({}).fetch();
        } else {
          freqs = Session.get("piechart_frozen");
        }

        if (computation.firstRun) {
          p = $('#pie').epoch({
            type: 'pie',
            height: $('#pie').height(),
            // initial data
            data: [
            { label: 'US', value: 1 },
            { label: 'GB', value: 1 },
            { label: 'CN', value: 1 },
            ]

          });
        }
        else {
          p.update(freqs, true)
        }
      })
 };

 Template.barchart.rendered = function () {
   this.autorun(function (computation) {
        //dependency to make code autorun when data changes
        Template.currentData();

        if (Session.get("control_btn_icon") == "pause") {
          barchart_freqs = BarData.find({}).fetch();
        } else {
          barchart_freqs = Session.get("barchart_frozen");
        }

        if (computation.firstRun) {
          barchart_handle = $('#barchart').epoch({
            type: 'pie',
            // initial data
            data: [
            { label: 'Society and social sciences', value: 1 },
            { label: 'Economy and Business', value: 1 }
            ]
          });
        }
        else {
          barchart_handle.update(barchart_freqs, true)
        }
      })
 };


}





if (Meteor.isServer) {
  Meteor.publish('edits', function() {
    return Edits.find({}, {sort: {createdAt: -1}, limit: 3});
  });

  Meteor.publish('piedata', function() {
    return PieData.find({}, {sort: {value: -1}, limit: 4});
  });

  Meteor.publish('bardata', function() {
    return BarData.find({}, {sort: {value: -1}, limit: 10});
  });

  Meteor.startup(function() {
    return Meteor.methods({
      clearPie: function() {
        PieData.remove({});
        var initialPieData = [
            { label: 'US', value: 1 },
            { label: 'GB', value: 1 },
            { label: 'CN', value: 1 },
            ]
        initialPieData.forEach(function(entry) {
          PieData.insert(entry);
        });
      },
      clearBar: function() {
        BarData.remove({});
        var initialData = [
            { label: 'Society and social sciences', value: 1 },
            { label: 'Economy and Business', value: 1 }
            ];
        initialData.forEach(function(entry) {
          BarData.insert(entry);
        });
      }
    }); // methods
  }); //startup
} // Meteor.isServer

