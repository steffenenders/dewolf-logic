"""Module testing world functions."""
import pytest

from simplifier.world.nodes import TmpVariable, Variable
from simplifier.world.world import World


class TestCompare:
    @pytest.mark.parametrize("condition", [("2@8"), ("z@4"), ("(~ a@2)"), ("(& a@2 b@2)"), ("(| a@2 b@2)")])
    def test_same_formula(self, condition):
        w = World()
        cond = w.from_string(condition)
        assert World.compare(cond, cond)

    @pytest.mark.parametrize("condition", [("2@8"), ("z@4"), ("(~ a@2)"), ("(& a@2 b@2)"), ("(| a@2 b@2)")])
    def test_same_order_formula(self, condition):
        w = World()
        cond = w.from_string(condition)
        assert World.compare(cond, w.from_string(condition))

    @pytest.mark.parametrize(
        "cond1, cond2", [("2@8", "2@4"), ("2@8", "5@8"), ("z@4", "y@4"), ("z@4", "(~ z@4)"), ("(| x@8 2@8)", "(| y@8 2@8)")]
    )
    def test_not_equal(self, cond1, cond2):
        w = World()
        assert not World.compare(w.from_string(cond1), w.from_string(cond2))

    @pytest.mark.parametrize("cond1, cond2", [("(& a@2 b@2)", "(& b@2 a@2)"), ("(| a@2 b@2)", "(| b@2 a@2)")])
    def test_switch_order_easy(self, cond1, cond2):
        w = World()
        assert World.compare(w.from_string(cond1), w.from_string(cond2))

    @pytest.mark.parametrize(
        "cond1, cond2", [("(& a@2 (| b@2 c@2))", "(& (| b@2 c@2) a@2)"), ("(| a@2 (& b@2 c@2))", "(| (& c@2 b@2) a@2)")]
    )
    def test_switch_order_with_operands(self, cond1, cond2):
        w = World()
        assert World.compare(w.from_string(cond1), w.from_string(cond2))

    @pytest.mark.parametrize(
        "var1, cond1, var2, cond2",
        [("v@2", "(& a@2 (| b@2 c@2))", "u@2", "(& (| b@2 c@2) a@2)"), ("v@2", "(| a@2 (& b@2 c@2))", "", "(| (& c@2 b@2) a@2)")],
    )
    def test_compare_with_variable(self, var1, cond1, var2, cond2):
        w = World()
        w.define(v1 := w.from_string(var1), w.from_string(cond1))
        w.define(v2 := w.from_string(var2), w.from_string(cond2)) if var2 else (v2 := w.from_string(cond2))
        assert World.compare(v1, v2)

    @pytest.mark.parametrize(
        "cond, definition, defined",
        [("(& b@2 u@2)", "1@2", "(& 1@2 b@2)"), ("(| a@2 u@2)", "(& b@2 c@2)", "(| a@2 (& b@2 c@2))")],
    )
    def test_compare_with_multiple_variable(self, cond, definition, defined):
        w = World()
        w.define(v := w.from_string("v@2"), w.from_string(cond))
        w.define(w.from_string("u@2"), w.from_string(definition))
        w.define(x := w.from_string("x@2"), w.from_string(defined))
        assert World.compare(v, w.from_string(defined))
        assert World.compare(v, x)

    def test_multiple_occurrence_of_operation(self):
        w1 = World()
        w2 = World()
        assert World.compare(
            w1.from_string("(& (| 2@8 (& a@8 b@8)) (| 4@8 (& a@8 b@8)) )"), w2.from_string("(& (| 4@8 (& a@8 b@8)) (| (& b@8 a@8) 2@8) )")
        )

    def test_double_operands_success(self):
        w = World()
        assert World.compare(
            w.bitwise_xor(w.variable("a", 2), w.variable("a", 2)),
            w.bitwise_xor(w.variable("a", 2), w.variable("a", 2)),
        )

    @pytest.mark.skip("Double after handling that operands also contains duplicates.")
    def test_double_operands_fail(self):
        w = World()
        assert not World.compare(
            w.bitwise_xor(w.variable("a", 2), w.variable("a", 2)),
            w.bitwise_xor(w.variable("a", 2)),
        )
        assert not World.compare(
            w.bitwise_xor(w.variable("a", 2), w.variable("a", 2)),
            w.bitwise_xor(w.variable("a", 2), w.variable("a", 2), w.variable("a", 2)),
        )


class TestWorld:
    def test_variable_add_twice(self):
        w = World()
        v = w.variable("v", 8)
        assert v == w.from_string("v @ 8")
        x = w.variable("x", 4)  # sanity check
        with pytest.raises(ValueError):
            w.variable("v", 4)
        with pytest.raises(ValueError):
            w.from_string("v@4")

    def test_variable_retrieve_undefined(self):
        w = World()
        v = w.variable("v", 8)
        assert v == w.variable("v")
        assert v == w.from_string("v")
        with pytest.raises(ValueError):
            w.variable("x")

    def test_variable_is_tmp_variable(self):
        w = World()
        v = w.tmp_variable("v", 8)
        assert v == TmpVariable(w, "v", 8)
        with pytest.raises(ValueError):
            w.variable("v", 8)

    def test_tmp_variable_can_not_be_normal_variable(self):
        w = World()
        v = w.variable("v", 8)
        assert v == w.variable("v")
        with pytest.raises(ValueError):
            w.tmp_variable("v", 8)

    def test_tmp_variable_can_only_only_be_added_once(self):
        w = World()
        v = w.tmp_variable("v", 8)
        assert v == TmpVariable(w, "v", 8)
        with pytest.raises(ValueError):
            w.tmp_variable("v", 8)

    def test_world_define_return(self):
        w = World()
        v = w.from_string("v@4 = (& x@4 y@4)")
        assert v is not None
        assert World.compare(v, w.from_string("(& x y)"))


class TestCleanUp:
    @pytest.mark.parametrize("term", ["v@4 = (& (| x@4 a@4) (| x@4 b@4))", "v@4 = (>> x@8 y@8)", "v@4", "v@4 = (~1@3)"])
    def test_do_nothing(self, term):
        w = World()
        w.from_string(term)
        w.cleanup()
        cmp_w = World()
        cmp_w.from_string(term)
        assert World.compare(w.from_string("v"), cmp_w.from_string("v"))

    @pytest.mark.parametrize(
        "term",
        [
            "(& (| 3@4 4@4) (| 3@4 1@4))",
            "(>> 15@8 3@8)",
            "1@4",
            "(~1@3)",
            "(Tmp)v@4 = (& (| 3@4 4@4) (| 2@4 1@4))",
            "(Tmp)v@4 = (>> 15@8 3@8)",
            "(Tmp)v@4",
            "(Tmp)v@4 = (~1@3)",
        ],
    )
    def test_remove_everything(self, term):
        w = World()
        w.from_string(term)
        w.cleanup()
        assert len(w) == 0

    @pytest.mark.parametrize(
        "term, numb_variables",
        [
            ("(& (| x@4 a@4) (| x@4 b@4))", 3),
            ("(>> x@8 y@8)", 2),
            ("(~x@3)", 1),
            ("(Tmp)v@4 = (& (| x@4 a@4) (| x@4 b@4))", 3),
            ("(Tmp)v@4 = (>> x@8 y@8)", 2),
            ("(Tmp)v@4 = (~x@3)", 1),
        ],
    )
    def test_remove_all_except_variables(self, term, numb_variables):
        w = World()
        w.from_string(term)
        w.cleanup()
        assert len(w) == numb_variables and all(isinstance(node, Variable) for node in w._graph)

    @pytest.mark.parametrize(
        "term1, term2, output, numb_vertices",
        [
            ("(& (| x@4 a@4) (| x@4 b@4))", "v@4 = (& (| (~x@4) a@4) (| x@4 c@4))", "v@4 = (& (| (~x@4) a@4) (| x@4 c@4))", 9),
            ("(~1@3)", "v@3 = (~2@3)", "v@3 = (~2@3)", 3),
            ("v@4 = (~z@5)", "(Tmp)w@4 = (>> x@8 y@8)", "v@4 = (~z@5)", 5),
            ("(Tmp)w@4 = (~x@5)", "v@4 = (~x@5)", "v@4 = (~x@5)", 3),
        ],
    )
    def test_remove_partially(self, term1, term2, output, numb_vertices):
        w = World()
        w.from_string(term1)
        w.from_string(term2)
        w.cleanup()
        cmp_w = World()
        cmp_w.from_string(output)
        assert World.compare(w.from_string("v"), cmp_w.from_string("v")) and len(w) == numb_vertices

    @pytest.mark.parametrize(
        "shared_operand, numb_vertices",
        [
            ("(& (| x@4 a@4) (| x@4 b@4))", 7),
            ("(~1@3)", 3),
            ("(>> x@8 y@8)", 4),
            ("(~x@5)", 3),
        ],
    )
    def test_shared_operand_1(self, shared_operand, numb_vertices):
        w = World()
        op = w.from_string(shared_operand)
        w.define(w.from_string("v@4"), op)
        w.define(w.from_string("(Tmp)w@4"), op)
        w.cleanup()
        cmp_w = World()
        assert w.compare(w.from_string("v"), cmp_w.from_string(shared_operand)) and len(w) == numb_vertices

    @pytest.mark.parametrize(
        "shared_operand, numb_vertices",
        [
            ("(& (| x@4 a@4) (| x@4 b@4))", 7),
            ("(~1@3)", 3),
            ("(>> x@8 y@8)", 4),
            ("(~x@5)", 3),
        ],
    )
    def test_shared_operand_2(self, shared_operand, numb_vertices):
        w = World()
        op = w.from_string(shared_operand)
        w.define(w.from_string("v@4"), op)
        w.define(w.from_string("(Tmp)w@4"), w.bitwise_negate(op))
        w.cleanup()
        cmp_w = World()
        assert w.compare(w.from_string("v"), cmp_w.from_string(shared_operand)) and len(w) == numb_vertices

    @pytest.mark.parametrize(
        "shared_operand, numb_vertices",
        [
            ("(& (| x@4 a@4) (| x@4 b@4))", 7),
            ("(~1@3)", 3),
            ("(>> x@8 y@8)", 4),
            ("(~x@5)", 3),
        ],
    )
    def test_shared_operand_3(self, shared_operand, numb_vertices):
        w = World()
        op = w.from_string(shared_operand)
        w.define(w.from_string("v@4"), op)
        w.define(w.from_string("(Tmp)w@4"), neg_op := w.bitwise_negate(op))
        w.define(w.from_string("(Tmp)z@4"), w.bitwise_and(neg_op, w.from_string("(| 1@4 c@4)")))
        w.cleanup()
        cmp_w = World()
        assert w.compare(w.from_string("v"), cmp_w.from_string(shared_operand)) and len(w) == numb_vertices + 1
