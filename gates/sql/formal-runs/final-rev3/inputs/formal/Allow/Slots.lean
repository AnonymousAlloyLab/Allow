import Allow.Canonical

namespace Allow.Slots

inductive Space where
  | signature | field | predicate | bound
  deriving DecidableEq, Repr

structure Slot where
  space : Space
  index : Nat
  deriving DecidableEq, Repr

inductive Operator where
  | module | signature | field | predicate | and | or | not | implies
  | join | product | union | intersection | difference | equal | subset
  | some | no | one | lone | all | exists | letBind | call | transpose
  | closure | reflexiveClosure | cardinality | ifThenElse | true | false
  deriving DecidableEq, Repr

/-- Closed tags, slots and typed scalar values: no arbitrary presentation string. -/
inductive Tree where
  | reference (slot : Slot)
  | number (value : Int)
  | node (operator : Operator) (children : List Tree)

structure Payload where
  profile : Nat
  declarations : List Tree
  facts : List Tree
  body : Tree

/-- Resolved structure is an elaborator input assumption, independent of names. -/
structure Presented where
  resolved : Payload
  names : Slot → String
  source : String
  origin : String

def anonymous (p : Presented) : Payload := p.resolved

structure EmbeddingInput where
  profile : Nat
  payload : Payload

def embedding (p : Presented) : EmbeddingInput := ⟨1, anonymous p⟩

theorem names_do_not_affect_payload (p : Presented) (labels : Slot → String) :
    anonymous {p with names := labels} = anonymous p := rfl

theorem names_do_not_affect_embedding (p : Presented) (labels : Slot → String)
    (source origin : String) :
    embedding {p with names := labels, source := source, origin := origin} = embedding p := rfl

theorem distinct_slots_remain_distinct (a b : Slot) (h : a ≠ b) :
    Tree.reference a ≠ Tree.reference b := by
  intro same
  exact h (Tree.reference.inj same)

theorem embedding_has_no_presentation (p : Presented) :
    embedding p = (⟨1, p.resolved⟩ : EmbeddingInput) := rfl

def demo : Payload := ⟨1, [], [], .reference ⟨.signature, 0⟩⟩

example : embedding ⟨demo, fun _ => "Person", "sig Person {}", "local-A"⟩ =
    embedding ⟨demo, fun _ => "SecretName", "sig SecretName {}", "local-B"⟩ := rfl

example : (Tree.reference ⟨.signature, 0⟩) ≠ Tree.reference ⟨.signature, 1⟩ := by
  apply distinct_slots_remain_distinct
  decide
example : (Tree.reference ⟨.signature, 0⟩) ≠ Tree.reference ⟨.bound, 0⟩ := by
  apply distinct_slots_remain_distinct
  decide

end Allow.Slots
