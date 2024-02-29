import JSON3, DisplayAs
import {{ module }}
_response = Dict("documentation" => string(@doc( {{ module }} )))
_response |> DisplayAs.unlimited ∘ JSON3.write