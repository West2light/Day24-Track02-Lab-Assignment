package medviet.data_access

import future.keywords.if
import future.keywords.in

default allow := false
default blocked := false

# Global hard-stop rules. Any matching condition blocks access regardless of role.
blocked if {
    input.data_classification == "restricted"
    input.destination_country != "VN"
}

blocked if {
    input.user.role == "ml_engineer"
    input.resource == "production_data"
    input.action == "delete"
}

# Expose deny as a convenience decision for explicit policy checks.
deny if {
    blocked
}

allow if {
    input.user.role == "admin"
    not blocked
}

allow if {
    input.user.role == "ml_engineer"
    input.resource in {"training_data", "model_artifacts", "aggregated_metrics"}
    input.action in {"read", "write"}
    not blocked
}

allow if {
    input.user.role == "data_analyst"
    (
        input.resource == "aggregated_metrics"
        input.action == "read"
    )
    not blocked
}

allow if {
    input.user.role == "data_analyst"
    (
        input.resource == "reports"
        input.action == "write"
    )
    not blocked
}

allow if {
    input.user.role == "intern"
    input.resource == "sandbox_data"
    input.action in {"read", "write"}
    not blocked
}
