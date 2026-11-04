import WarmPool
set_option format.width 1000000
set_option pp.universes true
#check @Allow.WarmPool.local_preserves_safety
#print axioms Allow.WarmPool.local_preserves_safety
#check @Allow.WarmPool.local_preserves_standby_bound
#print axioms Allow.WarmPool.local_preserves_standby_bound
#check @Allow.WarmPool.local_preserves_active_bound
#print axioms Allow.WarmPool.local_preserves_active_bound
#check @Allow.WarmPool.local_slot_unchanged
#print axioms Allow.WarmPool.local_slot_unchanged
#check @Allow.WarmPool.step_preserves_safety
#print axioms Allow.WarmPool.step_preserves_safety
#check @Allow.WarmPool.reachable_safety
#print axioms Allow.WarmPool.reachable_safety
#check @Allow.WarmPool.two_live_reservations
#print axioms Allow.WarmPool.two_live_reservations
#check @Allow.WarmPool.at_most_one_unassigned
#print axioms Allow.WarmPool.at_most_one_unassigned
#check @Allow.WarmPool.at_most_one_assigned
#print axioms Allow.WarmPool.at_most_one_assigned
#check @Allow.WarmPool.distinct_slot_owners
#print axioms Allow.WarmPool.distinct_slot_owners
#check @Allow.WarmPool.first_request_count_order
#print axioms Allow.WarmPool.first_request_count_order
#check @Allow.WarmPool.second_request_count_order
#print axioms Allow.WarmPool.second_request_count_order
#check @Allow.WarmPool.no_busy_to_ready
#print axioms Allow.WarmPool.no_busy_to_ready
#check @Allow.WarmPool.release_requires_cleanup
#print axioms Allow.WarmPool.release_requires_cleanup
#check @Allow.WarmPool.stale_release_rejected
#print axioms Allow.WarmPool.stale_release_rejected
#check @Allow.WarmPool.owned_release_refines_step
#print axioms Allow.WarmPool.owned_release_refines_step
#check @Allow.WarmPool.no_spawn_requires_never_attempted
#print axioms Allow.WarmPool.no_spawn_requires_never_attempted
#check @Allow.WarmPool.attempted_cannot_use_no_spawn
#print axioms Allow.WarmPool.attempted_cannot_use_no_spawn
#check @Allow.WarmPool.publish_requires_exit_fence_and_time
#print axioms Allow.WarmPool.publish_requires_exit_fence_and_time
#check @Allow.WarmPool.poison_prevents_publication
#print axioms Allow.WarmPool.poison_prevents_publication
#check @Allow.WarmPool.poison_sticky_same_generation
#print axioms Allow.WarmPool.poison_sticky_same_generation
#check @Allow.WarmPool.attempted_sticky_same_generation
#print axioms Allow.WarmPool.attempted_sticky_same_generation
#check @Allow.WarmPool.consumption_monotone_same_generation
#print axioms Allow.WarmPool.consumption_monotone_same_generation
#check @Allow.WarmPool.generation_changes_only_on_vacant_reservation
#print axioms Allow.WarmPool.generation_changes_only_on_vacant_reservation
#check @Allow.WarmPool.startup_deadline_checked
#print axioms Allow.WarmPool.startup_deadline_checked
#check @Allow.WarmPool.idle_deadline_checked
#print axioms Allow.WarmPool.idle_deadline_checked
#check @Allow.WarmPool.handoff_sets_clean_context
#print axioms Allow.WarmPool.handoff_sets_clean_context
#check @Allow.WarmPool.admission_deadline_not_reset
#print axioms Allow.WarmPool.admission_deadline_not_reset
#check @Allow.WarmPool.shutdown_is_absorbing
#print axioms Allow.WarmPool.shutdown_is_absorbing
#check @Allow.WarmPool.shutdown_forbids_publish
#print axioms Allow.WarmPool.shutdown_forbids_publish
#check @Allow.WarmPool.offline_step_preserves_delivery
#print axioms Allow.WarmPool.offline_step_preserves_delivery
#check @Allow.WarmPool.time_does_not_release
#print axioms Allow.WarmPool.time_does_not_release
#check @Allow.WarmPool.advisory_preserves_durable
#print axioms Allow.WarmPool.advisory_preserves_durable
#check @Allow.WarmPool.successful_one_use_witness
#print axioms Allow.WarmPool.successful_one_use_witness
#check @Allow.WarmPool.cancellation_after_fence_witness
#print axioms Allow.WarmPool.cancellation_after_fence_witness
#check @Allow.WarmPool.ready_and_fresh_coexist_witness
#print axioms Allow.WarmPool.ready_and_fresh_coexist_witness
