import unittest

from app.models.promotion import Promotion
from app.models.promotion_benefit import PromotionBenefit
from app.models.promotion_group import PromotionGroup
from app.models.promotion_product import PromotionProduct


class PromotionModelTests(unittest.TestCase):
    def test_promotion_table_mapping(self):
        self.assertEqual(Promotion.__tablename__, "promotions")

        self.assertIn("id", Promotion.__table__.c)
        self.assertIn("tenant_id", Promotion.__table__.c)
        self.assertIn("name", Promotion.__table__.c)
        self.assertIn("valid_from", Promotion.__table__.c)
        self.assertIn("valid_to", Promotion.__table__.c)
        self.assertIn("is_active", Promotion.__table__.c)

    def test_promotion_product_table_mapping(self):
        self.assertEqual(
            PromotionProduct.__tablename__,
            "promotion_products",
        )

        primary_key_columns = {
            column.name
            for column in PromotionProduct.__table__.primary_key.columns
        }

        self.assertEqual(
            primary_key_columns,
            {"promotion_id", "product_id"},
        )

    def test_promotion_group_table_mapping(self):
        self.assertEqual(
            PromotionGroup.__tablename__,
            "promotion_groups",
        )

        self.assertIn("promotion_id", PromotionGroup.__table__.c)
        self.assertIn("name", PromotionGroup.__table__.c)
        self.assertIn("selection_rule", PromotionGroup.__table__.c)

    def test_promotion_benefit_table_mapping(self):
        self.assertEqual(
            PromotionBenefit.__tablename__,
            "promotion_benefits",
        )

        self.assertIn("promotion_group_id", PromotionBenefit.__table__.c)
        self.assertIn("benefit_type", PromotionBenefit.__table__.c)
        self.assertIn("product_id", PromotionBenefit.__table__.c)
        self.assertIn("warranty_option_id", PromotionBenefit.__table__.c)
        self.assertIn("promotion_price", PromotionBenefit.__table__.c)
        self.assertIn("cashback_amount", PromotionBenefit.__table__.c)
        self.assertIn("payment_mode", PromotionBenefit.__table__.c)

    def test_promotion_group_selection_rule_constraint_exists(self):
        constraint_names = {
            constraint.name
            for constraint in PromotionGroup.__table__.constraints
        }

        self.assertIn(
            "ck_promotion_groups_selection_rule",
            constraint_names,
        )

    def test_promotion_benefit_type_constraint_exists(self):
        constraint_names = {
            constraint.name
            for constraint in PromotionBenefit.__table__.constraints
        }

        self.assertIn(
            "ck_promotion_benefits_type",
            constraint_names,
        )

    def test_promotion_benefit_field_constraint_exists(self):
        constraint_names = {
            constraint.name
            for constraint in PromotionBenefit.__table__.constraints
        }

        self.assertIn(
            "ck_promotion_benefits_valid_type_fields",
            constraint_names,
        )


if __name__ == "__main__":
    unittest.main()