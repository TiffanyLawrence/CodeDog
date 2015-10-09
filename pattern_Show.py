#/////////////////////////////////////////////////  R o u t i n e s   t o   G e n e r a t e  " m a i n ( ) "

import progSpec
import codeDogParser

showFuncCode=r"// No Main given"
def apply(objects, tags, nameOfStructToShow):
    print "pattern_Show........pattern_Show........pattern_Show........pattern_Show........pattern_Show........"
    print "pattern_Show........pattern_Show........pattern_Show........pattern_Show........pattern_Show........"
    #print objects
    #print tags
    print nameOfStructToShow
    
    obj=objects[0][nameOfStructToShow]
    #print obj

    tags['Include'] += ",<signal.h>"
    indent = "     "
    showFuncCode="\nfunc var "+ nameOfStructToShow +": show_"+nameOfStructToShow+'(<%infon* ITEM%>) <%{\n' + indent + 'string acc="";\n'
    
    for field in obj['fields']:
        
        kindOfField = field['kindOfField']
        fieldName = field['fieldName']
        #print kindOfField
        if (kindOfField == 'flag'):
            showFuncCode += indent+'acc += "'+fieldName+': " + (obj->flags & ' + fieldName + ')? "True":"False";\n'
        elif (kindOfField == 'mode'):
            showFuncCode += indent+'acc += enumText(&'+fieldName+'Strings, obj->flags, "fieldName", Offset'+');\n'
        elif ((kindOfField=="var" or kindOfField=="rPtr" or kindOfField=="sPtr" or kindOfField=="uPtr")):
            #if it's a struct and its in the object tree than must be codedog, else can't print
            #get base type in progspec
            fieldType = field['fieldType']
            baseType = progSpec.getTypesBase(fieldType)
            print kindOfField, fieldName, fieldType, baseType
            if (baseType=="int32" or baseType=="int64" or baseType=="double"  or baseType=="uint32" or baseType=="uint64" ):
                showFieldVal = '+ to_string(' + fieldName + ')'
            elif (baseType=="string" ):
                showFieldVal = '+ ' + fieldName 
            elif (baseType=="char"):
                showFieldVal = '+ ' + fieldName 
            elif (baseType=="bool"):
                showFieldVal = '+  (' + fieldName + ' ? "true": "false")'
            #elif (objects[0][fieldName]): 
                #if the field name is in the list of codeDog object names
                
                #showFieldVal = '+ show_pureInfon(&ITEM->'+ fieldName +')'
            else:
                showFieldVal = "can not print"
            #Do this last: dereference and print the base, make it remember which ones its done so it doesn't repeat, if it is a library, if its a codedog Struct
       
            showFuncCode += indent+'acc += "'+fieldName+':" ' + showFieldVal +';\n'
        else:   #other
            showFuncCode += indent+'acc += "'+fieldName+'": Can not print;\n'
     



    showFuncCode += '\n    }%>\n'


    print 'showFuncCode........showFuncCode........showFuncCode........showFuncCode'
    print showFuncCode


    progSpec.addObject(objects[0], objects[1], 'MAIN')
    codeDogParser.AddToObjectFromText(objects[0], objects[1], progSpec.wrapFieldListInObjectDef('MAIN', showFuncCode))
