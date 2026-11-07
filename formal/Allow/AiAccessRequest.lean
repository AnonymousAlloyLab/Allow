import Std

/- Abstract finite intake policy. Equality tokens abstract immutable request data.
   Clock, persistence, concurrency, SMTP, provider and implementation refinement are trusted. -/
namespace Allow.AiAccessRequest

structure Challenge where
  binding : Nat
  deadline : Nat
  attempts : Nat
  captcha : Bool
  email : Bool
  used : Bool
  deriving DecidableEq, Repr

def admitted (c : Challenge) (current now : Nat) (persisted : Bool) : Bool :=
  c.captcha && c.email && !c.used && c.binding == current &&
    decide (now < c.deadline ∧ c.attempts < 5) && persisted

def consume (c : Challenge) : Challenge := { c with used := true }
def tokenCount (_ : Challenge) : Nat := 0

theorem captcha_required (c : Challenge) (b n : Nat) (p : Bool) (h : c.captcha = false) :
    admitted c b n p = false := by simp [admitted, h]
theorem email_required (c : Challenge) (b n : Nat) (p : Bool) (h : c.email = false) :
    admitted c b n p = false := by simp [admitted, h]
theorem persistence_required (c : Challenge) (b n : Nat) :
    admitted c b n false = false := by simp [admitted]
theorem binding_required (c : Challenge) (b n : Nat) (p : Bool) (h : c.binding ≠ b) :
    admitted c b n p = false := by simp [admitted, h]
theorem used_denied (c : Challenge) (b n : Nat) (p : Bool) (h : c.used = true) :
    admitted c b n p = false := by simp [admitted, h]
theorem replay_denied (c : Challenge) (b n : Nat) (p : Bool) :
    admitted (consume c) b n p = false := by simp [admitted, consume]
theorem expiry_denied (c : Challenge) (b n : Nat) (p : Bool) (h : c.deadline ≤ n) :
    admitted c b n p = false := by
  have hn : ¬ n < c.deadline := by omega
  simp [admitted, hn]
theorem exhausted_denied (c : Challenge) (b n : Nat) (p : Bool) (h : 5 ≤ c.attempts) :
    admitted c b n p = false := by
  have hn : ¬ c.attempts < 5 := by omega
  simp [admitted, hn]
theorem no_token (c : Challenge) : tokenCount c = 0 := rfl

def witness : Challenge := ⟨7, 10, 0, true, true, false⟩
theorem positive : admitted witness 7 1 true = true := by decide
end Allow.AiAccessRequest
