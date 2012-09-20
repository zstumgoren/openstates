
$(document).ready(function() {

        var jsindex = {};
        var stemmer = new PorterStemmer();
        var body = $('body');

        $.getJSON(vsprintf('/media/js/turkeyvulture/index/%s.json', [abbr]), function(data){
            jsindex.index = data;
            console.log(vsprintf('/media/js/turkeyvulture/index/%s.json', [abbr]));
            });

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
                w = stemmer.stemWord(w.toLowerCase());

                // The word and stem ids.
                var word_id = this.index.stem2id[w];
                var stem_id = this.index.stem2id[w];

                // Query the index for a list of ids with
                // data that satisfy our query.
                var results = this.index.index[stem_id];
                objects = this.index.objects;

                // Query the object store to retrieve the full
                // record associated with each id.
                results = _.map(results, function(id){
                    return objects[id];
                    });

                // Regroup the objects by type.
                results = _.groupBy(results, '_type');

                // results.person = _.groupBy(results.person, 'chamber');
                // results.committee = _.groupBy(results.committee, 'chamber');

                // Replace undefined with list, mainly to play
                // nice with the template renderer, and also because
                // I suck at javascript.
                _.each(['person', 'committee'], function(k){

                    // Regroup the objects by chamber.
                    results[k] = _.groupBy(results[k], 'chamber');
                    if (results[k] === undefined){
                        results[k] = [];
                        }
                    });

                // Regroup the regrouped objects by chamber.
                //results.person =
                return results;
                },

            update: function(w){

                // Query the index.
                var results = this.query(w);

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

                        results[k] = {"__jsonjinja_wire__": "html-safe", "value": content};


                        // End if results...
                        } else {
                            delete results[k];
                        }
                    // End .each
                    });

                /* Render the layout. */
                results.abbr = abbr;
                var layout_name = 'layout.html';
                var layout_template = jsonjinja.getTemplate(layout_name);
                var content = layout_template.render(results);

                // Swap.
                $("#suggest").replaceWith(content);
                $("#suggest").hover(unblurfunc, blurfunc);

                // Highlight.
                $('#suggest-content').highlight(w);
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
