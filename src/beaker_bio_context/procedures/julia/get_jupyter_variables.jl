import JSON3, DisplayAs
IGNORED_SYMBOLS = [:Base, :Core, :InteractiveUtils, :Main]

file = open("/tmp/state.json", "w")

_state = Dict{Symbol, Any}(
    :user_vars => Dict{Symbol, String},
    :imported_modules => Symbol[]
)
_var_names = filter(x -> in(x, IGNORED_SYMBOLS), names(Main))
for var in _var_names
    value = eval(var)
    if isa(value, Module)
        push!(_state[:imported_modules], var)
    else
        _state[:user_vars][var] = string(value)
    end
end
_state |> DisplayAs.unlimited ∘ JSON3.write
