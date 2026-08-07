"""Model catalogue service.

Custom (derived) models layered on top of the base provider models. Admins
see the whole catalogue; other users only see models they own or that grant
them read access (resolved at the data layer). Mutations are gated at the
HTTP layer; this service just delegates to the models table.
"""

from typing import Optional

from jyotigpt.models.models import (
    ModelForm,
    ModelModel,
    ModelResponse,
    ModelUserResponse,
    Models,
)


class ModelCatalogue:
    def list_models(self, is_admin: bool, user_id: str) -> list[ModelUserResponse]:
        if is_admin:
            return Models.get_models()
        return Models.get_models_by_user_id(user_id)

    def list_base(self) -> list[ModelModel]:
        return Models.get_base_models()

    def get(self, id: str) -> Optional[ModelModel]:
        return Models.get_model_by_id(id)

    def create(self, form_data: ModelForm, user_id: str) -> Optional[ModelModel]:
        return Models.insert_new_model(form_data, user_id)

    def toggle(self, id: str) -> Optional[ModelModel]:
        return Models.toggle_model_by_id(id)

    def update(self, id: str, form_data: ModelForm) -> Optional[ModelModel]:
        return Models.update_model_by_id(id, form_data)

    def delete(self, id: str) -> bool:
        return Models.delete_model_by_id(id)

    def delete_all(self) -> bool:
        return Models.delete_all_models()


models = ModelCatalogue()
