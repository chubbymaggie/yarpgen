/*
Copyright (c) 2015-2016, Intel Corporation

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

     http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
*/

#include "master.h"

unsigned int MAX_LOOP_NUM = 10;
unsigned int MIN_LOOP_NUM = 1;

Master::Master (std::string _folder) {
    this->folder = _folder;
    std::uniform_int_distribution<unsigned int> loop_num_dis(MIN_LOOP_NUM, MAX_LOOP_NUM);
    unsigned int loop_num = loop_num_dis(rand_gen);
    for (int i = 0; i < loop_num; ++i) {
        Loop tmp_loop;
        tmp_loop.random_fill (i);
        loops.push_back(tmp_loop);
    }
}

void Master::write_file (std::string of_name, std::string data) {
    std::ofstream out_file;
    out_file.open (folder + "/" + of_name);
    out_file << data;
    out_file.close ();
}

std::string Master::emit_main () {
    std::string ret = "#include \"init.h\"\n\n";
    ret += "extern void foo ();\n";
    ret += "extern uint64_t checksum ();\n";
    ret += "int main () {\n";
    ret += "\tfoo();\n";
    ret += "\tstd::cout << checksum () << std::endl;\n";
    ret += "\treturn 0;\n";
    ret += "}";
    write_file("driver.cpp", ret);
    return ret;
}

std::string Master::emit_init () {
    std::string ret = "#include \"init.h\"\n\n";
    for (auto i = loops.begin (); i != loops.end (); ++i) {
        ret += i->emit_array_def ();
        ret += "\n";
    }
    write_file("init.cpp", ret);
    return ret;
}

std::string Master::emit_func() {
    std::string ret = "#include \"init.h\"\n\n";
    ret += "void foo () {\n\t";
    for (auto i = loops.begin (); i != loops.end (); ++i) {
        ret += i->emit_body ();
        ret += "\n\t";
    }
    ret += "}\n";
    write_file("func.cpp", ret);
    return ret;
}

std::string Master::emit_check() {
    std::string ret = "#include \"init.h\"\n\n";
    ret += "uint64_t checksum () {\n\t";
    ret += "uint64_t ret = 0;\n\t";
    for (auto i = loops.begin (); i != loops.end (); ++i) {
        std::string iter_name = "i_" + i->get_out_num_str ();
        ret += "for (uint64_t " + iter_name + " = 0; " + iter_name + " < " + std::to_string(i->get_min_size ()) + "; ++" + iter_name + ") {\n\t";
        ret += i->emit_array_usage("\tret ^= ", true);
        ret += "}\n\n\t";
    }
    ret += "return ret;\n";
    ret += "}\n";
    write_file("check.cpp", ret);
    return ret;
}

std::string Master::emit_decl() {
    std::string ret = "#include <cstdint>\n";
    ret += "#include <iostream>\n";
    for (auto i = loops.begin (); i != loops.end (); ++i)
        ret += i->emit_array_decl("extern ");
    write_file("init.h", ret);
    return ret;
}