import JSON3
docs = Dict{Symbol, Any}()
functions = Symbol[]
for func in functions
    docs[func] = eval(:(@doc $func))
end

info = open("/tmp/info.json", "w")
write(info, JSON3.write(docs))
