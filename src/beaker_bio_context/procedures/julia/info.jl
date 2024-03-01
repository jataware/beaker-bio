import JSON3, DisplayAs
_IGNORED_SYMBOLS = [:Base, :Core, :InteractiveUtils, :Main]

_from_module = {{from_module | default("true") }}
_return_source = {{ return_source | default("false") }} # TODO: Use this with CodeTracking.jl
_selected_module = :{{ module | default("nothing") }}
_chosen_funcs_str = {{ function_names | default("[]") }}


_function_names = 
    if _from_module
        _module_names = 
            if !isnothing(selected_module)
                filter(x -> in(x, _IGNORED_SYMBOLS) && isa(x, Module), names(Main))
            else
                _selected_module
            end
        filter(!in(_modules_names), reduce(vcat, [names(mod) for mod in _module_names]))
    else
        split(_chosen_func_str, ",")
    end

_docs = Dict{Symbol, Any}()
for func in _function_names
    _docs[func] = eval(:(@doc $func))
end

_docs |> DisplayAs.unlimited ∘ JSON3.write
