import JSON3
IGNORED_SYMBOLS = [:Base, :Core, :InteractiveUtils, :Main]

file = open("/tmp/state.json", "w")

state = Dict{Symbol, Any}(
    :user_vars => Dict{Symbol, String},
    :imported_modules => Symbol[]
)
_var_names = names(Main)
for var in _var_names
    value = eval(var)
    if in(var, IGNORED_SYMBOLS)
        continue
    elseif isa(value, Module)
        push!(state[:imported_modules], var)
    else
        state[:user_vars][var] = string(value)
    end
end
write(file, JSON3.write(state))
