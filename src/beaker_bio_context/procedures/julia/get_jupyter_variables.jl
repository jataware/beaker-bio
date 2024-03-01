import JSON3, DisplayAs, Pkg
IGNORED_SYMBOLS = [:Base, :Core, :InteractiveUtils, :Main, :IGNORED_SYMBOLS]

_state = Dict(
    :user_vars => Dict(),
    :imported_modules => [],
    :available_modules => Symbol.(keys(Pkg.project().dependencies))
)
_is_hidden(x) = string(x)[1] == '_'
_var_names = filter(x -> !(in(x, IGNORED_SYMBOLS) || _is_hidden(x)), names(Main))
for var in _var_names
    value = eval(var)
    if isa(value, Module)
        push!(_state[:imported_modules], var)
    else
        _state[:user_vars][var] = string(value)
    end
end

_state[:available_modules] = filter(!in(_state[:imported_modules]), _state[:available_modules])
_state |> DisplayAs.unlimited ∘ JSON3.write
