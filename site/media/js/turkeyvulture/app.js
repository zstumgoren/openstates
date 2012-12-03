
$(document).ready(function() {

        var jsindex = {};
        var stemmer = new PorterStemmer();
        var body = $('body');

        // If js is enabled, suppress the browser's
        // autocomplete.
        var id_q = $("#id_q");
        $("#searchform").attr('autocomplete', 'off');
        id_q.attr('autocomplete', 'off');

        // Make the menu go away on blur.
        var blurfunc = function(){
            console.log('rebinding blur');
            id_q.blur(function(){
                $("#suggest").html('');
                });
            };
        var unblurfunc = function(){
            console.log('unbiding blur');
            id_q.unbind('blur');
            };

        _.extend(jsindex, {
            query: function(w){

                // Stem the word.
                var stem = stemmer.stemWord(w.toLowerCase()),
                    url = vsprintf('/media/js/turkeyvulture/build/index/%s/%s', [abbr, stem]),
                    res = {};

                $.ajaxSetup({async: false});
                $.getJSON(url, function(results){
                    _.each(['person', 'committee'], function(k){

                        // Regroup the objects by chamber.
                        results[k] = _.groupBy(results[k], 'chamber');
                        if (results[k] === undefined){
                            results[k] = [];
                            }
                        });

                    res.results = results;
                });
                $.ajaxSetup({async: true});
                return res['results'];
            },

            update: function(w){

                // Query the index.
                var results = this.query(w);

                // If there were no results, use a dummy result.
                if (results === undefined) {
                    results = {person: [], committee: []};
                }
                var column_count = 0;
                var columns = {};
                var template_names = {};

                _.each(['person', 'committee'], function(k){

                    var objs = results[k];
                    var count = (objs.lower || []).length + (objs.upper || []).length;
                    if (count !== 0){

                        // Add thing_count to the context for each thing.
                        results[k + '_count'] = count;

                        // Choose which templates to use.
                        template_name = k + '.html';

                        // Render the columns.
                        var template = jsonjinja.getTemplate(template_name);
                        var context = {
                            objects: results[k],
                            object_type: k,
                            count: count};
                        var content = template.render(context);

                        results[k + '_data'] = results[k];
                        results[k] = {"__jsonjinja_wire__": "html-safe", "value": content};


                        // End if results...
                        } else {
                            delete results[k];
                        }
                    // End .each
                    });

                /* Render the layout. */
                results.abbr = abbr;
                results.searchterm = w;
                var layout_name = 'layout.html';
                var layout_template = jsonjinja.getTemplate(layout_name);
                var content = layout_template.render(results);

                // Are there results?
                var lengths = [
                    ((results.person_data || []).upper || []).length,
                    ((results.person_data || []).lower || []).length,
                    ((results.committee_data || []).upper || []).length,
                    ((results.committee_data || []).lower || []).length,
                    ((results.committee_data || []).joint || []).length];

                // Swap, but only if there are results.
                if (_.reduce(lengths, function(x, y){return x + y;})){
                        $("#suggest").replaceWith(content);
                        $("#suggest").hover(unblurfunc, blurfunc);
                        $('#suggest-content').highlight(w);
                    } else {
                        $("#suggest").html('');
                    }
                }
            });

        window.jsindex = jsindex;

        var search_input = $('#id_q');
        search_input.bind('keyup', function(e){
            e.preventDefault();
            var text = $(this).val();
            if (1 < text.length){
                jsindex.update(text);
                }
            else if( text.length === 0){
                // If text is empty, get rid of the content pane.
                $("#suggest").html('');
                }
            });
        //search_input.focus();
   });
