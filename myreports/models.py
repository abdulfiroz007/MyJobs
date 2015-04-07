import json
from django.db import models
from django.db.models.loading import get_model


class Report(models.Model):
    name = models.CharField(max_length=50)
    created_by = models.ForeignKey('myjobs.User')
    owner = models.ForeignKey('seo.Company')
    created_on = models.DateTimeField(auto_now_add=True)
    app = models.CharField(default='mypartners', max_length=50)
    model = models.CharField(default='contactrecord', max_length=50)
    # included columns and sort order
    values = models.CharField(null=True, max_length=500)
    # json encoded string of the params used to filter
    params = models.TextField()
    results = models.FileField(upload_to='reports')

    def __init__(self, *args, **kwargs):
        super(Report, self).__init__(*args, **kwargs)
        if self.results:
            self._results = self.results.read()
        else:
            self._results = '{}'

    @property
    def json(self):
        return self._results

    @property
    def python(self):
        python = json.loads(self._results)
        values = json.loads(self.values)

        if values:
            python = [{val: record[val] for val in values}
                      for record in python]

        return python

    @property
    def queryset(self):
        model = get_model(self.app, self.model)
        params = json.loads(self.params)
        values = json.loads(self.values)

        queryset = model.objects.from_search(self.owner, params)

        # If a report has values, we want specific columns, and rows which are
        # distinct on those columns. However, we also want access to the other
        # attributes of hte model, so `values()` isn't sufficient.
        if values:
            # Dear Django, please devise a way to do distinct on column with
            # MySQL so I don't have to do such hackery
            queryset = queryset.values(*values).distinct()
            pks = [model.objects.filter(**query).first().pk
                   for query in queryset]

            queryset = model.objects.filter(pk__in=pks)

        return queryset
