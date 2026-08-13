from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.http import require_POST

from apps.core.selectors import user_has_permission

from .forms import ItemForm
from .selectors import item_get, item_list
from .services import item_create, item_delete, item_update


def example_manage_required(view_func):
    return user_passes_test(
        can_manage_example,
        login_url="/dashboard/login/",
    )(view_func)


def can_manage_example(user) -> bool:
    return user.is_authenticated and (
        user.is_staff
        or user.is_superuser
        or user_has_permission(user=user, permission="example:manage")
    )


def item_or_404(item_id: str):
    item = item_get(item_id=item_id)
    if item is None:
        raise Http404("Item not found.")
    return item


@method_decorator(login_required(login_url="/dashboard/login/"), name="dispatch")
class ItemListView(View):
    def get(self, request: HttpRequest) -> HttpResponse:
        filters = {}
        search = request.GET.get("search", "").strip()
        if search:
            filters["search"] = search
        return render(
            request,
            "example/item_list.html",
            {
                "items": item_list(filters=filters),
                "search": search,
                "can_manage": can_manage_example(request.user),
            },
        )


@method_decorator(example_manage_required, name="dispatch")
class ItemCreateView(View):
    def get(self, request: HttpRequest) -> HttpResponse:
        return render(request, "example/item_form.html", {"form": ItemForm()})

    def post(self, request: HttpRequest) -> HttpResponse:
        form = ItemForm(request.POST)
        if not form.is_valid():
            return render(request, "example/item_form.html", {"form": form})
        item = item_create(**form.cleaned_data)
        return redirect("example:detail", pk=str(item.id))


@method_decorator(login_required(login_url="/dashboard/login/"), name="dispatch")
class ItemDetailView(View):
    def get(self, request: HttpRequest, pk: str) -> HttpResponse:
        return render(
            request,
            "example/item_detail.html",
            {"item": item_or_404(pk), "can_manage": can_manage_example(request.user)},
        )


@method_decorator(example_manage_required, name="dispatch")
class ItemUpdateView(View):
    def get(self, request: HttpRequest, pk: str) -> HttpResponse:
        item = item_or_404(pk)
        return render(request, "example/item_form.html", {"form": ItemForm(instance=item), "item": item})

    def post(self, request: HttpRequest, pk: str) -> HttpResponse:
        item = item_or_404(pk)
        form = ItemForm(request.POST, instance=item)
        if not form.is_valid():
            return render(request, "example/item_form.html", {"form": form, "item": item})
        item_update(item_id=pk, **form.cleaned_data)
        return redirect("example:detail", pk=pk)


@method_decorator(example_manage_required, name="dispatch")
class ItemDeleteView(View):
    @method_decorator(require_POST)
    def post(self, request: HttpRequest, pk: str) -> HttpResponse:
        item_delete(item_id=pk)
        return redirect("example:list")
